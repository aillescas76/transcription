import os

from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QFileDialog,
    QProgressDialog, QApplication
)
from PyQt6.QtGui import QIcon

from desktop.src.workers.transcription_worker import TranscriptionWorker
from desktop.src.views.theme_mixin import ThemeMixin


class MainWindow(QMainWindow, ThemeMixin):
    theme_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", "app_icon.svg")
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle("Desktop Audio App")
        self.resize(1024, 768)

        self.settings = QSettings("Milu", "Transcription")

        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Add top bar for the theme toggle button
        top_bar_layout = QHBoxLayout()
        top_bar_layout.addStretch()  # push items to the right
        self.theme_button = QPushButton()
        self.theme_button.clicked.connect(self.toggle_theme)
        top_bar_layout.addWidget(self.theme_button)
        # Insert the top bar layout at the top of the main layout
        main_layout.insertLayout(0, top_bar_layout)

        # -- Raw Text Section --
        raw_label = QLabel("Raw Text")
        self.raw_text_edit = QTextEdit()
        self.raw_text_edit.setReadOnly(True)
        main_layout.addWidget(raw_label)
        main_layout.addWidget(self.raw_text_edit)

        # -- Processed Text Section --
        processed_label = QLabel("Processed Text")
        self.processed_text_edit = QTextEdit()
        self.processed_text_edit.setReadOnly(True)
        main_layout.addWidget(processed_label)
        main_layout.addWidget(self.processed_text_edit)

        # -- Insights Section --
        insights_label = QLabel("Insights")
        self.insights_text_edit = QTextEdit()
        self.insights_text_edit.setReadOnly(True)
        main_layout.addWidget(insights_label)
        main_layout.addWidget(self.insights_text_edit)

        # -- Record and Transcribe Buttons --
        button_layout = QHBoxLayout()
        self.record_button = QPushButton("Record")
        self.record_button.setIcon(QIcon("desktop/icons/mic_24dp.svg"))
        self.record_button.clicked.connect(self.open_record_dialog)

        self.transcribe_button = QPushButton("Transcribe")
        self.transcribe_button.setIcon(QIcon("desktop/icons/description_24dp.svg"))
        self.transcribe_button.clicked.connect(self.open_file_selector)

        button_layout.addWidget(self.record_button)
        button_layout.addWidget(self.transcribe_button)
        button_layout.addStretch()  # Adjust placement as needed
        main_layout.addLayout(button_layout)

        # Set the central widget and layout
        self.setCentralWidget(central_widget)
        self.initialize_theme()

    def open_record_dialog(self):
        from desktop.src.views.record_dialog import RecordDialog
        dialog = RecordDialog(self)
        dialog.exec()

    def update_transcription(self, text):
        self.raw_text_edit.setPlainText(text)

    def open_file_selector(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Transcribe",
            "",
            "Audio Files (*.mp3 *.wav *.m4a);;All Files (*)"
        )
        if file_path:
            self.raw_text_edit.setPlainText("Transcription in progress...")

            progress_dialog = QProgressDialog("Initializing transcription...", "Cancel", 0, 0, self)
            progress_dialog.setWindowTitle("Transcription Progress")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.show()

            self.worker = TranscriptionWorker(file_path)
            self.worker.transcription_ready.connect(self.update_transcription)
            self.worker.progress_update.connect(progress_dialog.setLabelText)
            self.worker.finished.connect(progress_dialog.close)
            self.worker.start()

