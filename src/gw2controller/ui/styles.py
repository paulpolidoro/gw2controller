APP_QSS = """
QWidget {
    background: #F4F6F8;
    color: #1F2937;
    font-family: "Segoe UI";
    font-size: 13px;
}
QMainWindow, QDialog {
    background: #F4F6F8;
}
QTabWidget::pane {
    border: 1px solid #D5DCE6;
    border-radius: 10px;
    top: -1px;
    background: #FFFFFF;
}
QTabBar::tab {
    background: #E8EEF5;
    color: #4B5563;
    padding: 8px 16px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QTabBar::tab:selected {
    background: #FFFFFF;
    color: #111827;
    font-weight: 600;
}
QGroupBox {
    background: #FFFFFF;
    border: 1px solid #D5DCE6;
    border-radius: 12px;
    margin-top: 14px;
    padding: 14px 12px 12px 12px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #2563EB;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QListWidget, QTableWidget {
    background: #FFFFFF;
    color: #111827;
    border: 1px solid #C5CEDA;
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}
QComboBox QAbstractItemView {
    background: #FFFFFF;
    color: #111827;
    selection-background-color: #DBEAFE;
    selection-color: #1E3A8A;
}
QHeaderView::section {
    background: #EEF2F7;
    color: #374151;
    border: none;
    padding: 8px;
    font-weight: 600;
}
QTableWidget {
    gridline-color: #E5EAF1;
    selection-background-color: #DBEAFE;
    selection-color: #1E3A8A;
    alternate-background-color: #F8FAFC;
}
QPushButton {
    background: #FFFFFF;
    color: #1F2937;
    border: 1px solid #C5CEDA;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #EEF2F7;
}
QPushButton:pressed {
    background: #2563EB;
    color: #FFFFFF;
}
QPushButton:disabled {
    color: #9CA3AF;
    background: #F3F4F6;
}
QPushButton#primary {
    background: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
}
QPushButton#primary:hover {
    background: #1D4ED8;
}
QPushButton#danger {
    background: #FEE2E2;
    color: #991B1B;
    border: 1px solid #FECACA;
}
QCheckBox, QLabel, QRadioButton {
    background: transparent;
    color: #1F2937;
}
QRadioButton {
    spacing: 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 9px;
    border: 2px solid #94A3B8;
    background: #FFFFFF;
}
QRadioButton::indicator:hover {
    border-color: #2563EB;
}
QRadioButton::indicator:checked {
    border: 2px solid #2563EB;
    background: qradialgradient(
        cx: 0.5, cy: 0.5, radius: 0.5,
        fx: 0.5, fy: 0.5,
        stop: 0 #FFFFFF,
        stop: 0.35 #FFFFFF,
        stop: 0.45 #2563EB,
        stop: 1 #2563EB
    );
}
QRadioButton::indicator:disabled {
    border-color: #CBD5E1;
    background: #F1F5F9;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 2px solid #94A3B8;
    background: #FFFFFF;
}
QCheckBox::indicator:hover {
    border-color: #2563EB;
}
QCheckBox::indicator:checked {
    border: 2px solid #1D4ED8;
    background: #2563EB;
}
QCheckBox::indicator:checked:hover {
    background: #1D4ED8;
}
QCheckBox::indicator:disabled {
    border-color: #CBD5E1;
    background: #F1F5F9;
}
QCheckBox::indicator:checked:disabled {
    border-color: #93C5FD;
    background: #93C5FD;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #D5DCE6;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: #2563EB;
}
QStatusBar {
    background: #EEF2F7;
    color: #4B5563;
}
QMenu {
    background: #FFFFFF;
    color: #1F2937;
    border: 1px solid #D5DCE6;
}
QMenu::item:selected {
    background: #DBEAFE;
    color: #1E3A8A;
}
QScrollBar:vertical {
    background: #F4F6F8;
    width: 12px;
}
QScrollBar::handle:vertical {
    background: #C5CEDA;
    border-radius: 6px;
    min-height: 24px;
}
"""
