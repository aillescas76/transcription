import sys
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QLabel, QWidget
)
from PyQt6.QtCore import QSettings
from desktop.src.views.theme_mixin import ThemeMixin
from desktop.src.workers.record_worker import RecordWorker
import soundcard as sc
import sounddevice as sd
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


class RecordDialog(QDialog, ThemeMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Audio")
        self.resize(600, 300)

        # Initialize settings from parent if available, otherwise create new
        if parent and hasattr(parent, "settings"):
            self.settings = parent.settings
        else:
            self.settings = QSettings("Milu", "Transcription")

        # Initialize theme before UI setup
        self.initialize_theme()

        self.setup_ui()

        # Connect to parent's theme changed signal if available
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
