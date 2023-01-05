import sys

import screeninfo
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

from App.main import main


class Example(QWidget):

    def __init__(self):
        super().__init__()

        self.button_show_100 = QPushButton('Показать первые 100 записей')
        self.button_show_100.setMinimumHeight(50)
        self.button_show_100.clicked.connect(self.button_clicked)

        self.button_show_1000 = QPushButton('Показать первую 1000 записей')
        self.button_show_1000.setMinimumHeight(50)
        self.button_show_1000.clicked.connect(self.button_clicked)

        self.button_show_all = QPushButton('Показать все записи')
        self.button_show_all.setMinimumHeight(50)
        self.button_show_all.clicked.connect(self.button_clicked)

        self.pixmap = QPixmap("../Map/map_crop_with_dots.png")
        self.pixmap.setDevicePixelRatio(1.5)
        self.lbl = QLabel()
        self.lbl.setPixmap(self.pixmap.scaledToHeight(950, mode=Qt.TransformationMode.SmoothTransformation))

        self.button_layout = QFormLayout()
        self.button_layout.addWidget(self.button_show_100)
        self.button_layout.addWidget(self.button_show_1000)
        self.button_layout.addWidget(self.button_show_all)
        self.button_layout.setFormAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_layout = QGridLayout()
        self.image_layout.addWidget(self.lbl)

        self.main_container = QHBoxLayout()
        self.main_container.addLayout(self.button_layout)
        self.main_container.addLayout(self.image_layout)

        self.setLayout(self.main_container)

        self.setWindowTitle('Aqua Map')

        self.move(250, 10)
        # self.showNormal()
        self.showMaximized()

    def button_clicked(self):
        if self.sender() == self.button_show_all:
            main(nrows=None)
        elif self.sender() == self.button_show_100:
            main(nrows=100)
        elif self.sender() == self.button_show_1000:
            main(nrows=1000)

        self.pixmap = QPixmap("../Map/map_crop_with_dots.png")
        self.pixmap.setDevicePixelRatio(1.5)
        self.lbl.setPixmap(self.pixmap.scaledToHeight(950, mode=Qt.TransformationMode.SmoothTransformation))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec())
