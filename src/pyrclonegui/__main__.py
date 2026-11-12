import sys
from typing import Optional

from PyQt6.QtWidgets import QApplication, QStyle, QStyleFactory
# from qt_material import list_themes, apply_stylesheet

from pyrclonegui import PyRclone


def _main() -> int:
    app = QApplication(sys.argv)
    style: Optional[QStyle] = app.style()
    available_styles = [x.lower() for x in QStyleFactory.keys()]
    # print(f"Available styles: {available_styles}")
    # print(f"{list_themes()}")
    if "fusion" in available_styles and style is not None:
        style_name: str = style.name().lower()
        if style_name == "windows":
            new_style_name = "Fusion"
        elif style_name == "windowsvista":
            new_style_name = "Fusion"
        elif style_name == "windows11":
            new_style_name = "Fusion"
        else:
            new_style_name = style.name()
        qstyle: Optional[QStyle] = QStyleFactory.create(new_style_name)
        app.setStyle(qstyle)

    # apply_stylesheet(app, theme='dark_teal.xml', invert_secondary=False)
    # qstyle: QStyle = QStyleFactory.create("Windows")
    # app.setStyle(qstyle)
    # if style is not None and (style.name() == "windows11" or style.name() == "windowsvista"):
    #     app.setStyle(QStyleFactory.create('Fusion'))
    # app.setStyle(QStyleFactory.create('windows11'))
    pyrcloneg = PyRclone()
    pyrcloneg.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(_main())
