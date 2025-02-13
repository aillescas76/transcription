from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton
)

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Desktop Audio App")
        
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
        
        # -- Record Button --
        button_layout = QHBoxLayout()
        self.record_button = QPushButton("Record")
        self.record_button.clicked.connect(self.open_record_dialog)
        button_layout.addStretch()  # push button to the right or center as you see fit
        button_layout.addWidget(self.record_button)
        main_layout.addLayout(button_layout)
        
        # Set the central widget and layout
        self.setCentralWidget(central_widget)

    def open_record_dialog(self):
        # TODO: instantiate and show the floating Record Dialog with mic/sound selectors.
        # For now, simply print to console to confirm the button action.
        print("Record dialog should open now.")
