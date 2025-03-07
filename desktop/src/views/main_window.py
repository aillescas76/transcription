import os
from desktop.src.workers.transcription_worker import TranscriptionWorker
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QFileDialog,
    QProgressDialog
)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Desktop Audio App")
        self.resize(1024, 768)

        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Add top bar for the theme toggle button
        self.dark_mode = False  # initial mode is light
        top_bar_layout = QHBoxLayout()
        top_bar_layout.addStretch()  # push items to the right
        self.theme_button = QPushButton("Dark Mode")
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
        self.record_button.clicked.connect(self.open_record_dialog)
        self.transcribe_button = QPushButton("Transcribe")
        self.transcribe_button.clicked.connect(self.open_file_selector)
        button_layout.addWidget(self.record_button)
        button_layout.addWidget(self.transcribe_button)
        button_layout.addStretch()  # Adjust placement as needed
        main_layout.addLayout(button_layout)

        # Set the central widget and layout
        self.setCentralWidget(central_widget)

    def open_record_dialog(self):
        # TODO: instantiate and show the floating Record Dialog with mic/sound selectors.
        # For now, simply print to console to confirm the button action.
        print("Record dialog should open now.")

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
            
    def toggle_theme(self):
        from PyQt6.QtWidgets import QApplication
        if self.dark_mode:
            # Switch to light theme with explicit text colors for visibility
            style = """
                QMainWindow { background-color: #f0f0f0; color: #000000; }
                QProgressDialog { background-color: #ffffff; border: 1px solid #cccccc; color: #000000; }
                QPushButton { background-color: #1976d2; color: #ffffff; border-radius: 5px; padding: 8px 16px; }
                QPushButton:hover { background-color: #1565c0; }
                QLabel { font-family: "Segoe UI", sans-serif; font-size: 14px; color: #000000; }
                QTextEdit { background-color: #ffffff; border: 1px solid #cccccc; font-family: "Segoe UI", sans-serif; font-size: 12px; color: #000000; }
            """
            self.theme_button.setText("Dark Mode")
            self.dark_mode = False
        else:
            # Switch to dark theme with improved contrast and visible text
            style = """
                QMainWindow { background-color: #2b2b2b; color: #e0e0e0; }
                QProgressDialog { background-color: #333333; border: 1px solid #555555; color: #e0e0e0; }
                QPushButton { background-color: #546e7a; color: #e0e0e0; border-radius: 5px; padding: 8px 16px; }
                QPushButton:hover { background-color: #455a64; }
                QLabel { font-family: "Segoe UI", sans-serif; font-size: 14px; color: #e0e0e0; }
                QTextEdit { background-color: #424242; border: 1px solid #555555; font-family: "Segoe UI", sans-serif; font-size: 12px; color: #e0e0e0; }
            """
            self.theme_button.setText("Light Mode")
            self.dark_mode = True

        # Apply the new style globally
        QApplication.instance().setStyleSheet(style)

