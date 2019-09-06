import json

from wrappers.dandere2x_gui_wrapper import Dandere2x_Gui_Wrapper
from dandere2xlib.utils.dandere2x_utils import get_operating_system

if "linux" in get_operating_system():
    with open("dandere2x_linux.json", "r") as read_file:
        config_json = json.load(read_file)
        
else:
    with open("dandere2x_win32.json", "r") as read_file:
        config_json = json.load(read_file)

d = Dandere2x_Gui_Wrapper(config_json)

d.start()
