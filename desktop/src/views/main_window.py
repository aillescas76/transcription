from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QFileDialog
)
from PyQt6.QtCore import QThread, pyqtSignal

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Desktop Audio App")
        self.resize(1024, 768)
        
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
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
            self.worker = TranscriptionWorker(file_path)
            self.worker.transcription_ready.connect(self.update_transcription)
            self.worker.start()


class TranscriptionWorker(QThread):
    transcription_ready = pyqtSignal(str)

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self):
        try:
            import os
            from groq import Groq

            import os
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
