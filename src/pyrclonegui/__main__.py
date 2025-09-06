import sys

from PyQt6.QtWidgets import QApplication

from pyrclonegui import PyRclone


def _main() -> int:
    app = QApplication(sys.argv)
    # style: Optional[QStyle] = app.style()
    # if style is not None and style.name() == "windows11":
    #     app.setStyle(QStyleFactory.create('Fusion'))
    pyrcloneg = PyRclone()
    pyrcloneg.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(_main())
