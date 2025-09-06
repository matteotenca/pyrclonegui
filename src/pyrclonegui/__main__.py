import sys
from typing import Optional

from PyQt6.QtWidgets import QApplication, QStyle, QStyleFactory

from pyrclonegui import PyRcloneGui


def _main() -> int:
    app = QApplication(sys.argv)
    style: Optional[QStyle] = app.style()
    if style is not None and style.name() == "windows11":
        app.setStyle(QStyleFactory.create('Fusion'))
    pyrclonegui = PyRcloneGui()
    # pyrclonegui.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(_main())
