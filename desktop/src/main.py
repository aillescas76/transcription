import sys
import os
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from desktop.src.views.main_window import MainWindow

load_dotenv()  # Load environment variables from .env before anything else

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Build absolute path to the app icon
    icon_path = os.path.join(os.path.dirname(__file__), "..", "icons", "app_icon.svg")
    app.setWindowIcon(QIcon(icon_path))
    app.setStyleSheet("""
        QMainWindow { background-color: #f0f0f0; color: #000000; }
        QProgressDialog { background-color: #ffffff; border: 1px solid #cccccc; color: #000000; }
        QPushButton { background-color: #1976d2; color: #ffffff; border-radius: 5px; padding: 8px 16px; }
        QPushButton:hover { background-color: #1565c0; }
        QLabel { font-family: "Segoe UI", sans-serif; font-size: 14px; color: #000000; }
        QTextEdit { background-color: #ffffff; border: 1px solid #cccccc; font-family: "Segoe UI", sans-serif; font-size: 12px; color: #000000; }
    """)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
