import os
from os.path import join, dirname, abspath
from PyQt6.QtGui import QPalette, QColor, QIcon
from PyQt6.QtWidgets import QApplication

class ThemeMixin:
    """
    A mixin class that provides theme functionality for Qt widgets.
    
    This mixin expects the following attributes to be available:
    - self.settings: QSettings object for storing theme preference
    - self.setPalette: Method to set the widget's palette
    - self.setStyleSheet: Method to set the widget's stylesheet
    """
    
    def initialize_theme(self):
        """Initialize the theme from settings"""
        self.dark_mode = self.settings.value("dark_mode", False, type=bool)
        self.apply_theme()
        
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        self.dark_mode = not self.dark_mode
        self.settings.setValue("dark_mode", self.dark_mode)
        self.apply_theme()
        if hasattr(self, 'theme_changed'):
            self.theme_changed.emit(self.dark_mode)
    
    def apply_theme(self):
        """Apply the current theme to the widget"""
        palette = QPalette()
        if self.dark_mode:
            # Dark mode colors
            palette.setColor(QPalette.ColorRole.Window, QColor("#1F1C2C"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#e0e0e0"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#424242"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1F1C2C"))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1F1C2C"))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#e0e0e0"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#e0e0e0"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#5B86E5"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.Link, QColor("#5B86E5"))

            # Set theme button icon
            if hasattr(self, 'theme_button'):
                light_icon = os.path.join(os.path.dirname(__file__), "..", "..", "icons", "light_mode_24dp.svg")
                self.theme_button.setIcon(QIcon(light_icon))
        else:
            # Light mode colors
            palette.setColor(QPalette.ColorRole.Window, QColor("#f0f0f0"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#000000"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f0f0f0"))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#000000"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#000000"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#1976d2"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.Link, QColor("#1976d2"))

            # Set theme button icon
            if hasattr(self, 'theme_button'):
                dark_icon = os.path.join(os.path.dirname(__file__), "..", "..", "icons", "dark_mode_24dp.svg")
                self.theme_button.setIcon(QIcon(dark_icon))

        # Apply the palette to the application if this is the main window
        if isinstance(self, QApplication.activeWindow().__class__):
            QApplication.instance().setPalette(palette)

        # Apply the palette to this widget
        self.setPalette(palette)

        # Apply to central widget if it exists
        if hasattr(self, 'centralWidget') and self.centralWidget():
            self.centralWidget().setPalette(palette)

        # Load external QSS if available
        self._load_qss_stylesheet()

    def _load_qss_stylesheet(self):
        """Load the appropriate QSS stylesheet based on the theme"""
        # Determine the widget class name for the QSS file prefix
        class_name = self.__class__.__name__.lower()

        # Build the path to the QSS file
        base_path = join(dirname(abspath(__file__)), "..", "..", "styles")
        theme_suffix = "dark" if self.dark_mode else "light"
        qss_path = join(base_path, f"{class_name}_{theme_suffix}.qss")

        try:
            with open(qss_path, "r") as qss_file:
                qss = qss_file.read()
                self.setStyleSheet(qss)
        except Exception as e:
            print(f"Error loading QSS file {qss_path}: {e}")
