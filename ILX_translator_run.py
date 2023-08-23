from PyQt5.QtWidgets import QApplication
from ILX_translator_functions import MyMainWindow

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    MainWindow = MyMainWindow()
    MainWindow.show()
    sys.exit(app.exec_())