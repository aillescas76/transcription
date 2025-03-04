import sys
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication
from desktop.src.views.main_window import MainWindow

load_dotenv()  # Load environment variables from .env before anything else

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
