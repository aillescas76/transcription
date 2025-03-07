import os
import tempfile
import logging
from groq import Groq
from PyQt6.QtCore import QThread, pyqtSignal
from pydub import AudioSegment
from google import genai


def remove_leading_silence(sound, silence_thresh=-50.0, chunk_size=10):
    """
    Remove silence from the start of an AudioSegment.
    Returns the sliced AudioSegment.
    """
    trim_ms = 0  # in milliseconds
    # Iterate in small chunks until sound above threshold is found
    while trim_ms < len(sound) and sound[trim_ms:trim_ms + chunk_size].dBFS < silence_thresh:
        trim_ms += chunk_size
    return sound[trim_ms:]


def preprocess_audio(input_path):
    """
    Load an audio file, remove leading silence, set sample rate to 16000Hz,
    and export the processed audio to a temporary WAV file.
    Returns the path to the processed file.
    """
    try:
        # Load the original audio
        audio = AudioSegment.from_file(input_path)
        # Remove the leading silence
        audio = remove_leading_silence(audio)
        # Convert to 16kHz sample rate
        audio = audio.set_frame_rate(16000)
        # Export to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            processed_file_path = tmp.name
        audio.export(processed_file_path, format="wav")
        return processed_file_path
    except Exception as e:
        logging.error(f"Error in preprocess_audio: {e}")
        raise


def transcribe_single_file(processed_file_path, client, base_prompt):
    """
    Transcribe a single (non-chunked) file.
    Returns the transcription text.
    """
    with open(processed_file_path, "rb") as file:
        response = client.audio.transcriptions.create(
            file=(os.path.basename(processed_file_path), file.read()),
            model="whisper-large-v3-turbo",
            prompt=base_prompt,
            response_format="json",
            language="es",
            temperature=0.0
        )
    return response.text


def transcribe_chunks(processed_file_path, client, base_prompt, context_prefix, chunk_files_list, progress_callback=None):
    """
    Split the processed audio into time-based chunks (using pydub slicing),
    transcribe each with context from the previous, and return the full transcription.
    Also, append created chunk file paths to chunk_files_list.
    """
    # Load the audio ensuring proper WAV structure.
    audio_segment = AudioSegment.from_wav(processed_file_path)
    # Determine approximate chunk duration in ms.
    import math
    CHUNK_SIZE = 20 * 1024 * 1024  # 20MB
    bytes_per_second = audio_segment.frame_rate * audio_segment.channels * audio_segment.sample_width
    chunk_duration_ms = int((CHUNK_SIZE / bytes_per_second) * 1000)
    total_chunks = math.ceil(len(audio_segment) / chunk_duration_ms)
    logging.info(f"Calculated chunk duration: {chunk_duration_ms} ms (bytes per second: {bytes_per_second}).")

    base_dir = os.getcwd()
    prev_context = ""
    responses = []

    for i, start_ms in enumerate(range(0, len(audio_segment), chunk_duration_ms)):
        if progress_callback:
            progress_callback(f"Processing chunk {i+1} of {total_chunks}...")
        chunk = audio_segment[start_ms: start_ms + chunk_duration_ms]
        chunk_filename = os.path.splitext(os.path.basename(processed_file_path))[0] + f"_chunk{start_ms}.wav"
        chunk_filepath = os.path.join(base_dir, chunk_filename)
        # Export the chunk as a proper WAV file.
        chunk.export(chunk_filepath, format="wav")
        logging.info(f"Exported chunk starting at {start_ms} ms to file {chunk_filepath} with duration {len(chunk)} ms.")
        chunk_files_list.append(chunk_filepath)

        # Build prompt ensuring the total remains below the API limit of 896 characters.
        if prev_context:
            max_prompt_length = 224 - 1 - len(context_prefix)  # API maximum allowed characters
            truncated_context = prev_context[:max_prompt_length]
            prompt_text = f"{context_prefix}\n{truncated_context}\n"
        else:
            prompt_text = base_prompt

        with open(chunk_filepath, "rb") as cf:
            file_contents = cf.read()
            response = client.audio.transcriptions.create(
                file=(chunk_filename, file_contents),
                model="whisper-large-v3-turbo",
                prompt=prompt_text,
                response_format="json",
                language="es",
                temperature=0.0
            )
        transcription_text = response.text
        # Use the last paragraph of the transcription as context for the next chunk.
        paragraphs = transcription_text.strip().split("\n\n")
        prev_context = paragraphs[-1] if paragraphs else transcription_text

        responses.append(transcription_text)

    return "".join(responses)


def clean_text_with_gemini(transcription_text):
    """
    Use the Gemini API to clean up the transcribed text.
    Returns the cleaned text.
    """
    context = (
        "* Clean up the following text from an audio transcription.\n"
        "* Make the text coherent and try to identify participants in the conversation (participant_A, participant_B...).\n"
        "* This is the transciption text: \n"
        "'''\n"
        f"{transcription_text}\n"
        "'''\n"
    )
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=context,
    )
    return response.text


class TranscriptionWorker(QThread):
    transcription_ready = pyqtSignal(str)
    progress_update = pyqtSignal(str)

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self):
        try:
            self.progress_update.emit("Starting transcription process...")
            try:
                processed_file_path = preprocess_audio(self.file_path)
                chunk_files = []
                self.progress_update.emit("Audio preprocessing completed.")
            except Exception as e:
                logging.error(f"Error during preprocessing: {e}")
                self.transcription_ready.emit(f"Error during preprocessing: {str(e)}")
                return

            MAX_SIZE = 25 * 1024 * 1024  # 25MB
            context_prefix = "Use the following context from the previous chunk:\n"

            file_size = os.path.getsize(processed_file_path)
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))

            try:
                with open("technical_words.txt", "r", encoding="utf-8") as f:
                    tech_words = f.read().strip()
            except Exception as e:
                logging.error(f"Error reading technical words file: {e}")
                tech_words = ""

            base_prompt = (
                "Transcribe the audio ensuring the final transcription is in Spanish. "
                f"Use the following technical vocabulary as context: {tech_words}. "
                "If something is not clear, return nothing. "
            )

            if file_size > MAX_SIZE:
                final_transcription = transcribe_chunks(
                    processed_file_path, client, base_prompt, context_prefix, chunk_files,
                    progress_callback=lambda msg: self.progress_update.emit(msg)
                )
            else:
                self.progress_update.emit("Processing full file transcription...")
                final_transcription = transcribe_single_file(processed_file_path, client, base_prompt)

            # Clean up the transcribed text using Gemini
            self.progress_update.emit("Cleaning transcription using Gemini API...")
            try:
                final_transcription = clean_text_with_gemini(final_transcription)
            except Exception as e:
                logging.error(f"Error cleaning transcription with Gemini: {e}")

            self.transcription_ready.emit(final_transcription)

            # Clean up any chunk files created in the base directory
            if 'chunk_files' in locals():
                for chunk_file in chunk_files:
                    if os.path.exists(chunk_file):
                        try:
                            os.remove(chunk_file)
                            logging.info(f"Removed chunk file: {chunk_file}")
                        except Exception as rm_chunk_err:
                            logging.error(f"Error removing chunk file {chunk_file}: {rm_chunk_err}")

        except Exception as e:
            logging.error(f"Error during transcription: {e}")
            self.transcription_ready.emit(f"Error during transcription: {str(e)}")
        finally:
            # Ensure the processed file is removed
            if 'processed_file_path' in locals() and os.path.exists(processed_file_path):
                try:
                    os.remove(processed_file_path)
                    logging.info(f"Removed processed temporary file: {processed_file_path}")
                except Exception as rm_err:
                    logging.error(f"Error removing processed file {processed_file_path}: {rm_err}")
