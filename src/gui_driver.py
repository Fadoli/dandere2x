"""
The gui part of dandere2x
Mostly written in QT by aka_katto
Not much to optimize here other than
looks and minimalism?
"""

import json
import os
import sys

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog

from gui.Dandere2xGUI import Ui_Dandere2xGUI
from wrappers.dandere2x_gui_wrapper import Dandere2x_Gui_Wrapper
from dandere2xlib.utils.dandere2x_utils import get_operating_system

class QtDandere2xThread(QtCore.QThread):
    finished = QtCore.pyqtSignal()

    def __init__(self, parent, config_json):
        super(QtDandere2xThread, self).__init__(parent)
        self.config_json = config_json


    def run(self):
        d2x_main = Dandere2x_Gui_Wrapper(self.config_json)

        try:
            d2x_main.start()

        except Exception as e: #yeah, too general exception here
            print("dandere2x could not start for some reason.\n If you're on Windows try running as admin?")
            print("The error was:\n", e)

        self.finished.emit()


class AppWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.ui = Ui_Dandere2xGUI()
        self.ui.setupUi(self)

        # load 'this folder' in a pyinstaller friendly way
        self.this_folder = os.getcwd()

        if getattr(sys, 'frozen', False):
            self.this_folder = os.path.dirname(sys.executable) + os.path.sep
        elif __file__:
            self.this_folder = os.path.dirname(__file__) + os.path.sep

        # lazy hack_around for linux build (im not sure why the previous statement doesnt work on venv linux)
        if get_operating_system() == "linux":
            self.this_folder = os.getcwd()

        self.input_file = ''
        self.output_file = ''
        self.scale_factor = None
        self.noise_level = None
        self.image_quality = None
        self.block_size = ''
        self.waifu2x_type = ''
        self.use_default_name = True

        # not really necessary to init this var here, just to be sure
        self.thread = None

        # define a standart font
        self.font = QtGui.QFont("Yu Gothic UI Semibold", 11, QtGui.QFont.Bold)

        # theres a bug with qt designer and '80' for default quality needs to be set elsewhere
        _translate = QtCore.QCoreApplication.translate
        self.ui.image_quality_box.setCurrentText(_translate("Dandere2xGUI", "85"))
        self.ui.block_size_combo_box.setCurrentText(_translate("Dandere2xGUI", "20"))
        self.ui.waifu2x_type_combo_box.setCurrentText(_translate("Dandere2xGUI", "Waifu2x-Vulkan"))
        
        # self.ui.video_icon.setPixmap(QtGui.QPixmap("assets\\aka.png"))

        self.config_buttons()
        self.refresh_scale_factor()
        self.show()

    # Setup connections for each button
    def config_buttons(self):
        self.ui.select_video_button.clicked.connect(self.press_select_video_button)
        self.ui.select_output_button.clicked.connect(self.press_select_output_button)
        self.ui.upscale_button.clicked.connect(self.press_upscale_button)
        self.ui.waifu2x_type_combo_box.currentIndexChanged.connect(self.refresh_scale_factor)

        # The following connects are to re-adjust the file name

        noise_radio_list = [self.ui.noise_0_radio_button, self.ui.noise_1_radio_button,
                            self.ui.noise_2_radio_button, self.ui.noise_3_radio_button]

        for radio in noise_radio_list:
            radio.clicked.connect(self.refresh_output_file)

        scale_radio_list = [self.ui.scale_1_radio_button, self.ui.scale_2_radio_button,
                            self.ui.scale_3_radio_button, self.ui.scale_4_radio_button]

        for radio in scale_radio_list:
            radio.clicked.connect(self.refresh_output_file)

        self.ui.waifu2x_type_combo_box.currentIndexChanged.connect(self.refresh_output_file)
        self.ui.block_size_combo_box.currentIndexChanged.connect(self.refresh_output_file)
        self.ui.image_quality_box.currentIndexChanged.connect(self.refresh_output_file)

    # if vulkan is enabled, we cant do scale factor 3 or 4

    # refresh the buttons to see if upscale can be called
    def refresh_buttons(self):
        # allow user to upscale if two output_file are met
        if self.input_file != '' and self.output_file != '':
            self.ui.upscale_button.setEnabled(True)
            self.ui.upscale_status_label.setFont(self.font)
            self.ui.upscale_status_label.setText("Ready to upscale!")

    def refresh_output_file(self):
        if self.input_file == '':
            return

        if not self.use_default_name:
            return

        self.parse_gui_inputs()

        path, name = os.path.split(self.input_file)
        name_only = name.split(".")[0]

        self.output_file = os.path.join(path, (name_only + "_"
                                               + "[" + str(self.waifu2x_type) + "]"
                                               + "[s" + str(self.scale_factor) + "]"
                                               + "[n" + str(self.noise_level) + "]"
                                               + "[b" + str(self.block_size) + "]"
                                               + "[q" + str(self.image_quality) + "]" + ".mkv"))

        self.set_output_file_name()

    def refresh_scale_factor(self):
        if self.ui.waifu2x_type_combo_box.currentText() == 'Waifu2x-Vulkan':
            self.ui.scale_3_radio_button.setEnabled(False)
            self.ui.scale_4_radio_button.setEnabled(False)
            self.ui.scale_1_radio_button.setEnabled(False)
        else:
            self.ui.scale_3_radio_button.setEnabled(True)
            self.ui.scale_4_radio_button.setEnabled(True)
            self.ui.scale_1_radio_button.setEnabled(True)

    def press_upscale_button(self):

        self.ui.upscale_status_label.setFont(self.font)
        self.ui.upscale_status_label.setText("Upscaling in Progress")
        self.ui.upscale_status_label.setStyleSheet('color: #fad201')

        self.parse_gui_inputs()

        print(os.getcwd())

        if get_operating_system() == 'win32':
            with open(os.path.join(self.this_folder, "dandere2x_win32.json"), "r") as read_file:
                config_json = json.load(read_file)

        elif get_operating_system() == 'linux':
            with open(os.path.join(self.this_folder, "dandere2x_linux.json"), "r") as read_file:
                config_json = json.load(read_file)

        config_json['dandere2x']['usersettings']['output_file'] = self.output_file
        config_json['dandere2x']['usersettings']['input_file'] = self.input_file
        config_json['dandere2x']['usersettings']['block_size'] = self.block_size
        config_json['dandere2x']['usersettings']['image_quality'] = self.image_quality
        config_json['dandere2x']['usersettings']['waifu2x_type'] = self.waifu2x_type
        config_json['dandere2x']['usersettings']['scale_factor'] = self.scale_factor

        print("output_file = " + self.output_file)
        print("input_file = " + self.input_file)
        print("block_size = " + str(self.block_size))
        print("image_quality = " + str(self.image_quality))
        print("waifu2x_type = " + self.waifu2x_type)

        self.thread = QtDandere2xThread(self, config_json)
        self.thread.finished.connect(self.update)

        self.disable_buttons()

        try:
            self.thread.start()

        except Exception as error: #yup, too broad exception here

            print("Oops!", error, "occured.")
            self.ui.upscale_status_label.setFont(self.font)
            self.ui.upscale_status_label.setText("Upscale Failed. See log")

    def disable_buttons(self):
        self.ui.upscale_button.setEnabled(False)
        self.ui.select_output_button.setEnabled(False)
        self.ui.select_video_button.setEnabled(False)

    def enable_buttons(self):
        self.ui.upscale_button.setEnabled(True)
        self.ui.select_output_button.setEnabled(True)
        self.ui.select_video_button.setEnabled(True)

    def update(self):
        self.ui.upscale_status_label.setFont(self.font)
        self.ui.upscale_status_label.setText("Upscale Complete!")
        self.ui.upscale_status_label.setStyleSheet('color: #27FB35')
        self.thread.terminate()
        self.enable_buttons()

    # Parse everything we need from the GUI into a dandere2x friendly format
    # Leave everything as STR's since config files are just strings
    def parse_gui_inputs(self):

        # fuck windows and it's file management system 
        # [tremx] LMAO XD the double backward slash is a pain IKR
        if get_operating_system() == 'win32':
            self.output_file = self.output_file.replace("/", "\\")
            self.input_file = self.input_file.replace("/", "\\")

        # Scale Factors

        if self.ui.scale_1_radio_button.isChecked():
            self.scale_factor = 1

        if self.ui.scale_2_radio_button.isChecked():
            self.scale_factor = 2

        if self.ui.scale_3_radio_button.isChecked():
            self.scale_factor = 3

        if self.ui.scale_4_radio_button.isChecked():
            self.scale_factor = 4

        # Noise factors

        if self.ui.noise_0_radio_button.isChecked():
            self.noise_level = 0

        if self.ui.noise_1_radio_button.isChecked():
            self.noise_level = 1

        if self.ui.noise_2_radio_button.isChecked():
            self.noise_level = 2

        if self.ui.noise_3_radio_button.isChecked():
            self.noise_level = 3

        # Dandere2x Settings

        self.image_quality = int(self.ui.image_quality_box.currentText())
        self.block_size = int(self.ui.block_size_combo_box.currentText())

        # Waifu2x Type
        if self.ui.waifu2x_type_combo_box.currentText() == 'Waifu2x-Caffe':
            self.waifu2x_type = 'caffe'

        if self.ui.waifu2x_type_combo_box.currentText() == 'Waifu2x-Vulkan':
            self.waifu2x_type = 'vulkan'

        if self.ui.waifu2x_type_combo_box.currentText() == 'Waifu2x-Converter-Cpp':
            self.waifu2x_type = "converter_cpp"

    def press_select_video_button(self):

        self.input_file = self.load_file()[0]

        if self.input_file == '':
            return

        #[tremx]
        path, name = os.path.split(self.input_file)
        #path is unused here but initialized, maybe it's better doing a
        #name = os.path.split(self.input_file)[1]
        #since that what we want?

        # set the video label to the selected file name
        self.ui.video_label.setText(name)
        self.ui.video_label.setFont(self.font)

        # parse inputs so we can access variables
        self.parse_gui_inputs()

        # make a default name

        self.refresh_output_file()

        self.set_output_file_name()
        self.refresh_buttons()

    def press_select_output_button(self):

        save_file_name = self.save_file_name()

        if save_file_name == '':
            return

        self.output_file = save_file_name
        self.use_default_name = False

        # If the user didn't select anything, don't continue or it'll break
        # Everything
        if self.output_file == '':
            return

        self.set_output_file_name()

        self.refresh_buttons()

    def set_output_file_name(self):

        # set the label to only display the last 20 elements of the selected workspace
        start_val = len(self.output_file) - 28
        if start_val < 0:
            start_val = 0

        self.ui.workspace_label.setText(".." + self.output_file[start_val:  len(self.output_file)])
        self.ui.workspace_label.setFont(QtGui.QFont("Yu Gothic UI Semibold", 8, QtGui.QFont.Bold))

    def load_dir(self):
        self.ui.w = QWidget()

        self.ui.w.resize(320, 240)
        filename = QFileDialog.getExistingDirectory(w, 'Open Directory', self.this_folder)
        return filename

    def save_file_name(self):
        self.ui.w = QWidget()

        #[tremx] filter is already a python native function, renaming to d2x_filter
        d2x_filter = "Images (*.mkv *.mp4)"
        self.ui.w.resize(320, 240)

        default_name = self.output_file
        if self.output_file == '':
            default_name = self.this_folder

        filename = QFileDialog.getSaveFileName(w, 'Save File', default_name, d2x_filter)
        return filename[0]

    def load_file(self):
        self.ui.w = QWidget()

        self.ui.w.resize(320, 240)
        filename = QFileDialog.getOpenFileName(w, 'Open File', self.this_folder)
        return filename


app = QApplication(sys.argv)
w = AppWindow()
w.setWindowTitle("Test")
w.show()
sys.exit(app.exec_())
