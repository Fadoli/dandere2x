# For the GUI to work around

from dandere2xlib.utils.dandere2x_utils import dir_exists, wait_on_delete_dir
from dandere2x import Dandere2x
from context import Context

import shutil
import time
import os


class Dandere2x_Gui_Wrapper:
    """
    A wrapper to call dandere2x.py from the GUI. The extra-added faetures are clearing the workspace ahead of time
    and deleting the files after run-time, if gui_delete_workspace_after json is set to true.
    """
    def __init__(self, config_file):
        self.config_file = config_file
        self.context = Context(config_file)

    def start(self):
        print(self.context.workspace)

        if dir_exists(self.context.workspace):
            print("Deleted Folder")
            # TODO: we can't shutil.rmtree a ramdisk directory
            # ignore_errors = True fixes?
            shutil.rmtree(self.context.workspace, ignore_errors=True)

        wait_on_delete_dir(self.context.workspace)
        try:
            os.mkdir(self.context.workspace)
        except OSError:
            print("Creation of directory failed")

        # starting shit
        print("Starting Dandere2x")
        d = Dandere2x(self.context)
        d.run_concurrent()
        d.context.close_logger()

        if d.context.config_file['dandere2x']['developer_settings']['gui_delete_workspace_after']:
            d.delete_workspace_files()

        print("Dandere2x GUI Run Finished Successfully")