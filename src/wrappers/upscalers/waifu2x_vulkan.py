from dandere2xlib.utils.dandere2x_utils import file_exists, get_lexicon_value, rename_file, wait_on_either_file
from dandere2xlib.utils.json_utils import get_options_from_section
from context import Context

import subprocess
import threading
import logging
import shutil
import copy
import time
import glob
import os


class Waifu2xVulkan(threading.Thread):
    """
    The waifu2x-vulkan wrapper, with custom functions written that are specific for dandere2x to work.
    """

    def __init__(self, context: Context, d2x_main):
        # load context
        self.frame_count = context.frame_count
        self.waifu2x_ncnn_vulkan_file_path = context.waifu2x_ncnn_vulkan_file_path
        self.waifu2x_ncnn_vulkan_path = context.waifu2x_ncnn_vulkan_path
        self.residual_images_dir = context.residual_images_dir
        self.residual_for_upscale = context.residual_for_upscale
        self.residual_upscaled_dir = context.residual_upscaled_dir
        self.noise_level = context.noise_level
        self.scale_factor = context.scale_factor
        self.workspace = context.workspace
        self.minimal_disk_processing = context.minimal_disk_processing
        self.max_frames_ahead = context.max_frames_ahead
        self.context = context

        self.waifu2x_vulkan_upscale_frame = [self.waifu2x_ncnn_vulkan_file_path,
                                             "-i", "[input_file]",
                                             "-n", str(self.noise_level),
                                             "-s", str(self.scale_factor)]

        waifu2x_vulkan_options = get_options_from_section(
            self.context.config_file["waifu2x_ncnn_vulkan"]["output_options"])

        # add custom options to waifu2x_vulkan
        for element in waifu2x_vulkan_options:
            self.waifu2x_vulkan_upscale_frame.append(element)

        self.waifu2x_vulkan_upscale_frame.extend(["-o", "[output_file]"])

        self.d2x_main = d2x_main

        threading.Thread.__init__(self)
        logging.basicConfig(filename=self.workspace + 'waifu2x.log', level=logging.INFO)

    def upscale_file(self, input_file: str, output_file: str):
        """
        Manually upscale a file using the wrapper.
        """

        # load context
        waifu2x_ncnn_vulkan_path = self.context.waifu2x_ncnn_vulkan_path
        exec_command = copy.copy(self.waifu2x_vulkan_upscale_frame)

        # replace the exec command with the files we're concerned with
        for x in range(len(exec_command)):
            if exec_command[x] == "[input_file]":
                exec_command[x] = input_file

            if exec_command[x] == "[output_file]":
                exec_command[x] = output_file

        # waifu2x-ncnn-vulkan requires the directory to be local when running, so use os.chir to work out of that dir.
        os.chdir(waifu2x_ncnn_vulkan_path)

        console_output = open(self.context.log_dir + "vulkan_upscale_frame.txt", "w")
        console_output.write(str(exec_command))
        subprocess.call(exec_command, shell=False, stderr=console_output, stdout=console_output)
        console_output.close()

     
    def move_files_dir(self, src, dst):
        for file_path in glob.glob(src + os.path.sep + '*'):
            shutil.move(file_path, dst)

    def delete_dir_contents(self, dir_files):
        folder = dir_files
        for item in os.listdir(folder):
            file_path = os.path.join(folder, item)
            if os.path.isfile(file_path):
                os.remove(file_path)


    def run(self):
        """
        Input:
            - Files made by residuals.py appearing in the /residual_images/ folder.

        Output:
            - Files upscaled in /residual_upscaled/

        Code Description:

        The current Dandere2x implementation requires files to be removed from the 'residual_images' folder
        during runtime. When waifu2x-ncnn-vulkan calls 'upscale folder', it will only upscale what's in the folder
        at that moment, and it'll re-upscale the images that it already upscaled in a previous iteration.

        Considering that residual_images produced by Dandere2x don't all exist during the initial
        Waifu2x call, we need to call the 'upscale folder' command multiple times. To prevent waifu2x from re-upscaling
        the same image twice, various work arounds are in place to allow Dandere2x and Waifu2x to work in real time.

        Briefly, 1) Create a list of names that will be upscaled by waifu2x,
                 2) Call waifu2x to upscale whatever images are in 'differences' folder
                 3) After waifu2x call is finished, delete whatever files were upscaled, and remove those names from list.
                   (this is to prevent Waifu2x from re-upscaling the same image again)
                 4) Repeat this process until all the names are removed.
        """

        logger = logging.getLogger(__name__)

        exec_command = copy.copy(self.waifu2x_vulkan_upscale_frame)

        with open(self.context.log_dir + "vulkan_upscale_frames.txt", "w") as console_output:

            # replace the exec command with the files we're concerned with
            for x in range(len(exec_command)):
                if exec_command[x] == "[input_file]":
                    exec_command[x] = self.residual_for_upscale

                if exec_command[x] == "[output_file]":
                    exec_command[x] = self.residual_upscaled_dir

            # we need to os.chdir to set the directory or else waifu2x-vulkan won't work.
            os.chdir(self.waifu2x_ncnn_vulkan_path)

            logger.info("waifu2x_vulkan session")
            logger.info(exec_command)

            while not self.d2x_main.stop_upscaler:
                
                # don't mix up already upscaled/pending residual files
                self.move_files_dir(self.residual_images_dir, self.residual_for_upscale)

                # if there's at least a bit of files to process in current "batch"
                # this worked some times but was pretty unstable, commenting
                #if len(os.listdir(self.residual_for_upscale)) + len(os.listdir(self.residual_upscaled_dir)) >= self.max_frames_ahead/2:
                subprocess.call(exec_command, shell=False, stderr=console_output, stdout=console_output)

                self.delete_dir_contents(self.residual_for_upscale)

                # calm down moving and calling subprocess
                time.sleep(0.1)