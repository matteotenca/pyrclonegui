"""Application stylesheet (light/dark)."""

LIGHT = dict(bg="#f4f6fa", panel="#ffffff", alt="#f7f9fc", text="#1f2430", muted="#6b7385", border="#dde2ea",
             accent="#3b6ef5", accent_hover="#2f5bd6", danger="#d9534f", danger_hover="#bf3f3b",
             header="#1f2a44", header_text="#ffffff", sel="#e3ebff", ok="#2e9e5b")
DARK = dict(bg="#171a21", panel="#1f2430", alt="#232938", text="#e6e9f0", muted="#9099ad", border="#2f364a",
            accent="#5b8cff", accent_hover="#7aa2ff", danger="#e5645f", danger_hover="#f07c77",
            header="#10131a", header_text="#ffffff", sel="#2c3a63", ok="#4cc38a")


def palette(dark: bool) -> dict:  # type: ignore[type-arg]
    return DARK if dark else LIGHT


def qss(dark: bool) -> str:
    c = palette(dark)
    return f"""
QMainWindow, QDialog {{ background: {c['bg']}; }}
QWidget {{ color: {c['text']}; font-size: 10pt; }}
QWidget#centralwidget, QWidget#bodyWidget {{ background: {c['bg']}; }}
QFrame#headerFrame {{ background: {c['header']}; }}
QFrame#headerFrame QLabel {{ color: {c['header_text']}; background: transparent; }}
QLabel#titleLabel {{ font-size: 15pt; font-weight: 600; padding-right: 10px; }}
QLabel#serverStatusLabel {{ color: #c5cbe0; }}
QPushButton {{ background: {c['panel']}; border: 1px solid {c['border']}; border-radius: 6px;
               padding: 6px 14px; }}
QPushButton:hover {{ border-color: {c['accent']}; }}
QPushButton:disabled {{ color: {c['muted']}; background: {c['alt']}; }}
QPushButton[role="primary"] {{ background: {c['accent']}; color: #ffffff; border: none; font-weight: 600; }}
QPushButton[role="primary"]:hover {{ background: {c['accent_hover']}; }}
QPushButton[role="danger"] {{ background: transparent; color: {c['danger']}; border: 1px solid {c['danger']}; }}
QPushButton[role="danger"]:hover {{ background: {c['danger']}; color: #ffffff; }}
QFrame#headerFrame QPushButton {{ background: transparent; color: #ffffff; border: 1px solid #4a5780; }}
QFrame#headerFrame QPushButton:hover {{ border-color: #ffffff; }}
QFrame#headerFrame QPushButton[role="primary"] {{ background: {c['accent']}; border: none; }}
QFrame#headerFrame QPushButton[role="primary"]:checked {{ background: {c['danger']}; }}
QFrame#headerFrame QPushButton:disabled {{ color: #7d86a3; }}
QLineEdit {{ background: {c['panel']}; border: 1px solid {c['border']}; border-radius: 6px; padding: 6px 10px;
             min-width: 220px; }}
QLineEdit:focus {{ border-color: {c['accent']}; }}
QTableWidget {{ background: {c['panel']}; alternate-background-color: {c['alt']}; border: 1px solid {c['border']};
                border-radius: 8px; selection-background-color: {c['sel']}; selection-color: {c['text']};
                outline: 0; }}
QTableWidget::item {{ padding: 4px 8px; border: none; }}
QHeaderView::section {{ background: {c['panel']}; color: {c['muted']}; border: none;
                        border-bottom: 1px solid {c['border']}; padding: 8px; font-weight: 600; }}
QTableWidget QPushButton {{ padding: 3px 0; }}
QMenuBar {{ background: {c['panel']}; }}
QMenuBar::item:selected, QMenu::item:selected {{ background: {c['sel']}; }}
QMenu {{ background: {c['panel']}; border: 1px solid {c['border']}; padding: 4px; }}
QMenu::item {{ padding: 5px 24px; border-radius: 4px; }}
QStatusBar {{ background: {c['panel']}; color: {c['muted']}; }}
QDockWidget {{ titlebar-close-icon: none; font-weight: 600; }}
QDockWidget::title {{ background: {c['panel']}; padding: 6px; }}
QPlainTextEdit {{ background: {c['panel']}; border: none; font-family: Consolas, 'DejaVu Sans Mono', monospace;
                  font-size: 9pt; }}
QToolTip {{ background: {c['panel']}; color: {c['text']}; border: 1px solid {c['border']}; }}
"""


def app_icon():  # type: ignore[no-untyped-def]
    """Window/tray icon drawn in code: white cloud on a blue rounded square."""
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPixmap

    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        u = size / 100.0
        grad = QLinearGradient(0, 0, 0, size)
        grad.setColorAt(0, QColor("#6f9bff"))
        grad.setColorAt(1, QColor("#2f56d6"))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(4 * u, 4 * u, 92 * u, 92 * u), 22 * u, 22 * u)
        cloud = QPainterPath()
        cloud.setFillRule(Qt.FillRule.WindingFill)
        cloud.addEllipse(QRectF(22 * u, 42 * u, 30 * u, 30 * u))
        cloud.addEllipse(QRectF(36 * u, 28 * u, 34 * u, 34 * u))
        cloud.addEllipse(QRectF(54 * u, 40 * u, 26 * u, 26 * u))
        cloud.addRoundedRect(QRectF(30 * u, 50 * u, 42 * u, 22 * u), 11 * u, 11 * u)
        p.setBrush(QColor("#ffffff"))
        p.drawPath(cloud.simplified())
        p.end()
        icon.addPixmap(pm)
    return icon
