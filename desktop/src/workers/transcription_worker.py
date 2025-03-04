import os
from groq import Groq
from PyQt6.QtCore import QThread, pyqtSignal

class TranscriptionWorker(QThread):
    transcription_ready = pyqtSignal(str)

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self):
        try:
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            with open(self.file_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(self.file_path, file.read()),
                    model="whisper-large-v3-turbo",
                    prompt="Specify context or spelling",
                    response_format="json",
                    language="en",
                    temperature=0.0
                )
            self.transcription_ready.emit(transcription.text)
        except Exception as e:
            self.transcription_ready.emit(f"Error during transcription: {str(e)}")
