import os
import sys
import subprocess
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QLabel, QWidget
)
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import QThread, pyqtSignal
import soundcard as sc
import sounddevice as sd
import soundfile as sf
import numpy as np
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

def get_default_sink_monitor():
    """Return the monitor source of the default sink using pactl info."""
    if not sys.platform.startswith("linux"):
        return None
    try:
        output = subprocess.check_output(["pactl", "info"], universal_newlines=True)
        for line in output.splitlines():
            if line.startswith("Default Sink:"):
                sink = line.split(":", 1)[1].strip()
                monitor = f"{sink}.monitor"
                logger.info(f"get_default_sink_monitor: Default sink monitor: {monitor}")
                return monitor
    except subprocess.CalledProcessError as err:
        logger.error(f"get_default_sink_monitor: Error querying default sink: {err}")
    return None

def get_monitor_source():
    """Return the first monitor source name from pactl, or None if not found."""
    if not sys.platform.startswith("linux"):
        return None
    # Try to get the monitor from the default sink first.
    monitor = get_default_sink_monitor()
    if monitor:
        return monitor
    try:
        output = subprocess.check_output(
            ['pactl', 'list', 'sources', 'short'], universal_newlines=True
        )
    except subprocess.CalledProcessError as err:
        logger.error(f"get_monitor_source: Error running pactl: {err}")
        return None

    for line in output.strip().splitlines():
        parts = line.split('\t')
        if len(parts) >= 2 and "monitor" in parts[1].lower():
            return parts[1]
    return None

def set_default_source(source_name):
    """Set the default audio input source using pactl."""
    try:
        subprocess.check_call(['pactl', 'set-default-source', source_name])
        logger.info(f"set_default_source: Default source set to {source_name}")
    except subprocess.CalledProcessError as err:
        logger.error(f"set_default_source: Error setting default source: {err}")

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
        import threading

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


class RecordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Audio")
        self.resize(600, 300)
        self.setup_ui()
        self.apply_theme()
        if self.parent() and hasattr(self.parent(), "theme_changed"):
            self.parent().theme_changed.connect(lambda dark: self.apply_theme())
        self.worker = None
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Device selection
        device_widget = QWidget()
        device_layout = QVBoxLayout(device_widget)
        
        # Microphone selection
        mic_layout = QHBoxLayout()
        mic_label = QLabel("Microphone:")
        self.mic_combo = QComboBox()
        mic_layout.addWidget(mic_label)
        mic_layout.addWidget(self.mic_combo)
        device_layout.addLayout(mic_layout)
        
        # System audio selection
        sys_layout = QHBoxLayout()
        sys_label = QLabel("System Audio:")
        self.sys_combo = QComboBox()
        sys_layout.addWidget(sys_label)
        sys_layout.addWidget(self.sys_combo)
        device_layout.addLayout(sys_layout)
        
        layout.addWidget(device_widget)
        
        # Record button
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_button)

        # Add information label to display selected device details
        self.info_label = QLabel("")
        layout.addWidget(self.info_label)
        
        # Update device info whenever the selection changes
        self.mic_combo.currentIndexChanged.connect(self.update_device_info)
        self.sys_combo.currentIndexChanged.connect(self.update_device_info)
        
        self.populate_devices()
        
    def populate_devices(self):
        # Populate microphone devices
        self.mics = sc.all_microphones()
        self.mic_combo.clear()
        for mic in self.mics:
            self.mic_combo.addItem(mic.name)
            
        # Populate system devices
        self.sys_devices = sd.query_devices()
        self.sys_combo.clear()
        # If on Linux, try auto-selecting the monitor source via pactl.
        monitor_source = get_monitor_source()
        auto_selected = False
        for i, dev in enumerate(self.sys_devices):
            if dev['max_input_channels'] > 0:
                self.sys_combo.addItem(f"{dev['name']}", i)
                if monitor_source and monitor_source.lower() in dev['name'].lower():
                    index = self.sys_combo.count() - 1
                    self.sys_combo.setCurrentIndex(index)
                    auto_selected = True
                    logger.info(f"RecordDialog: Auto-selected system device '{dev['name']}' (matches monitor: {monitor_source}).")
        if not auto_selected:
            logger.info("RecordDialog: No auto-detected monitor device found; using default selection.")

        # Update the device info label with the newly populated devices
        self.update_device_info()

    def toggle_recording(self):
        if self.worker is None or not self.worker.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        mic_device = self.mics[self.mic_combo.currentIndex()]
        sys_device_index = self.sys_combo.currentData()
        
        # On Linux, set the default source to the monitor source.
        # If no monitor device is found, create a virtual null sink for recording.
        if sys.platform.startswith("linux"):
            monitor_source = get_monitor_source()
            if not monitor_source:
                try:
                    subprocess.check_call(
                        ["pactl", "load-module", "module-null-sink", "sink_name=VirtualSink", "sink_properties=device.description=VirtualSink"]
                    )
                    logger.info("RecordDialog: Created virtual null sink 'VirtualSink'")
                except subprocess.CalledProcessError as err:
                    logger.error(f"RecordDialog: Error creating virtual sink: {err}")
                monitor_source = "VirtualSink.monitor"
            set_default_source(monitor_source)
            logger.info(f"RecordDialog: Setting default source to monitor: {monitor_source}")

        # Retrieve device default sample rates
        mic_info = self.mics[self.mic_combo.currentIndex()]
        mic_samplerate = getattr(mic_info, 'default_samplerate', 44100)
        sys_info = self.sys_devices[sys_device_index]
        sys_samplerate = sys_info.get('default_samplerate', 44100)
        # Use the system device default for capture
        selected_rate = int(sys_samplerate)
        logger.info(f"RecordDialog: Using sample rate {selected_rate} Hz for recording (system default).")
        logger.info(f"RecordDialog: Selected mic device: {mic_device.name}")
        logger.info(f"RecordDialog: Selected system device: {sys_info.get('name', 'Unknown')}")
        
        self.worker = RecordWorker(mic_device, sys_device_index)
        self.worker.samplerate = selected_rate  # Capture at device default rate
        self.worker.recording_finished.connect(self.on_recording_finished)
        self.worker.start()
        
        self.record_button.setText("Stop Recording")
    
    def stop_recording(self):
        if self.worker:
            logger.info("RecordDialog: Stopping recording.")
            self.worker.stop()
            self.worker.wait()  # Confirm the worker has stopped
        self.record_button.setText("Start Recording")
        self.close()  # Close the dialog after the worker has fully stopped
    
    def on_recording_finished(self, output_file):
        print(f"Recording saved to: {output_file}")

    def apply_theme(self):
        dark_mode = False
        if self.parent() is not None and hasattr(self.parent(), "dark_mode"):
            dark_mode = self.parent().dark_mode
        
        palette = QPalette()
        if dark_mode:
            # Improved dark mode palette for increased contrast.
            palette.setColor(QPalette.ColorRole.Window, QColor("#121212"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#1E1E1E"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#BB86FC"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#000000"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#FFFFFF"))
        else:
            palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#000000"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#1976d2"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#000000"))
        self.setPalette(palette)
        
        # --- Load external QSS for RecordDialog ---
        from os.path import join, dirname, abspath
        base_path = join(dirname(abspath(__file__)), "..", "..", "styles")
        qss_path = join(base_path, "record_dialog_dark.qss") if dark_mode else join(base_path, "record_dialog_light.qss")
        try:
            with open(qss_path, "r") as qss_file:
                qss = qss_file.read()
                self.setStyleSheet(qss)
        except Exception as e:
            print(f"Error loading QSS file {qss_path}: {e}")

    def update_device_info(self):
        mic_index = self.mic_combo.currentIndex()
        sys_device_index = self.sys_combo.currentData()
        if mic_index < 0 or sys_device_index is None:
            self.info_label.setText("")
            return
        mic = self.mics[mic_index]
        sys_info = self.sys_devices[sys_device_index]
        info_text = f"Mic: {mic.name}"
        if hasattr(mic, 'default_samplerate'):
            info_text += f" | Default Rate: {mic.default_samplerate} Hz"
        info_text += f"\nSystem: {sys_info.get('name', 'Unknown')}"
        if 'default_samplerate' in sys_info:
            info_text += f" | Default Rate: {sys_info.get('default_samplerate')} Hz"
        info_text += f" | Channels: {sys_info.get('max_input_channels')}"
        self.info_label.setText(info_text)
