import sys
from typing import Optional

from PyQt6.QtWidgets import QApplication, QStyle, QStyleFactory

from pyrclonegui import PyRclone


def _main() -> int:
    app = QApplication(sys.argv)
    style: Optional[QStyle] = app.style()
    available_styles = [x.lower() for x in QStyleFactory.keys()]

    if "fusion" in available_styles and style is not None:
        style_name: str = style.name().lower()
        if style_name == "windows":
            new_style_name = "Fusion"
        elif style_name == "windowsvista":
            new_style_name = "Fusion"
        elif style_name == "windows11":
            new_style_name = "Fusion"
        else:
            new_style_name = style_name
        qstyle: QStyle = QStyleFactory.create(new_style_name)
        app.setStyle(qstyle)

    # if style is not None and (style.name() == "windows11" or style.name() == "windowsvista"):
    #     app.setStyle(QStyleFactory.create('Fusion'))
    # app.setStyle(QStyleFactory.create('windows11'))
    pyrcloneg = PyRclone()
    pyrcloneg.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(_main())
