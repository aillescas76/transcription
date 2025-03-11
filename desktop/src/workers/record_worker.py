import os
from datetime import datetime
import threading
import numpy as np
import logging
from PyQt6.QtCore import QThread, pyqtSignal
import sounddevice as sd
import soundfile as sf

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")


class RecordWorker(QThread):
    recording_finished = pyqtSignal(str)

    def __init__(self, mic_device, sys_device_index):
        super().__init__()
        self.mic_device = mic_device
        self.sys_device_index = sys_device_index
        self.is_recording = False
        self.samplerate = 44100

    def run(self):
        self.is_recording = True
        logger.info("RecordWorker: Starting recording session.")

        stop_event = threading.Event()
        recordings = {"mic": [], "sys": []}
        blocksize = 1024

        def record_mic():
            logger.debug("RecordWorker: Starting microphone recording thread.")
            with self.mic_device.recorder(samplerate=self.samplerate, blocksize=blocksize) as rec:
                while not stop_event.is_set():
                    block = rec.record(numframes=blocksize)
                    recordings["mic"].append(block)
            logger.debug("RecordWorker: Exiting microphone recording thread.")

        def record_sys():
            logger.debug("RecordWorker: Starting system audio recording thread.")
            with sd.InputStream(samplerate=self.samplerate, blocksize=blocksize,
                                device=self.sys_device_index, channels=2) as stream:
                while not stop_event.is_set():
                    block, _ = stream.read(blocksize)
                    recordings["sys"].append(block)
            logger.debug("RecordWorker: Exiting system audio recording thread.")

        mic_thread = threading.Thread(target=record_mic)
        sys_thread = threading.Thread(target=record_sys)
        mic_thread.start()
        sys_thread.start()

        # Wait until stop is signaled via self.is_recording flag.
        # Use QThread's msleep for a responsive wait.
        while self.is_recording:
            self.msleep(100)
        stop_event.set()
        mic_thread.join()
        sys_thread.join()
        logger.info("RecordWorker: Recording threads have terminated. Processing recordings...")

        # Avoid concatenation errors when no blocks were recorded
        if not recordings["mic"] or not recordings["sys"]:
            print("No audio data recorded.")
            return

        # Process and combine recordings
        mic_data = np.concatenate(recordings["mic"], axis=0)
        sys_data = np.concatenate(recordings["sys"], axis=0)

        # Trim both recordings to the length of the shorter one.
        min_len = min(len(mic_data), len(sys_data))
        mic_data = mic_data[:min_len]
        sys_data = sys_data[:min_len]

        # If the mic data is mono, duplicate it to stereo.
        if sys_data.ndim == 2 and sys_data.shape[1] == 2 and mic_data.ndim == 2 and mic_data.shape[1] == 1:
            mic_data = np.tile(mic_data, (1, 2))

        combined = 0.5 * (sys_data + mic_data)

        # Resample combined audio to 16000 Hz if capture rate differs
        target_rate = 16000
        if self.samplerate != target_rate:
            try:
                from scipy.signal import resample_poly
                logger.info(f"RecordWorker: Resampling from {self.samplerate} Hz to {target_rate} Hz.")
                combined = resample_poly(combined, target_rate, self.samplerate, axis=0)
                self.samplerate = target_rate
            except ImportError:
                logger.error("RecordWorker: scipy not available for resampling. Skipping resample.")

        # Save the recording
        output_folder = "recordings"
        os.makedirs(output_folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_folder, f"recording_{timestamp}.wav")
        sf.write(output_file, combined, self.samplerate, subtype="PCM_16")
        self.recording_finished.emit(output_file)
        logger.info(f"RecordWorker: Recording finished. File saved to {output_file}")

    def stop(self):
        self.is_recording = False
