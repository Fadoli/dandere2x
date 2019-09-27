from dandere2xlib.utils.dandere2x_utils import file_exists, get_lexicon_value, rename_file, wait_on_either_file, move_files_dir, delete_dir_contents
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

    def __init__(self, context: Context):
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


    def run(self):
        """
        Input:
            - Files made by residuals.py appearing in the folder
              ./dandere2x/src/workspace/$workspace_name/processing/residual_images/*.(context.extension_type)

        Output:
            - Files upscaled in
              ./dandere2x/src/workspace/$workspace_name/processing/residual_upscaled/*.png

        Code Description:

        The current Dandere2x implementation requires files to be moved from the 'residual_images' folder to
        residual_for_upscale so when waifu2x-ncnn-vulkan calls 'upscale folder', it will only upscale what's in the folder
        at that moment ('residual_for_upscale') and shortly after the job is done, it'll delete the contents of
        residual_for_upscale directory so that no re-upscaling already upscaled files compute power is wasted.

        This process is called virtually infinite times in minimal-disk mode since works in batches of images,
        traditional methods hardly get called more than a couple of times since Waifu2x usually is miles
        behind the Dandere2x C++ script in upscaling the current residual images. That's because the buffer in
        residual_images since C++ is way ahead will be big, really big.

        Briefly, 1) Move every 'residual_image' to 'residual_to_upscale'

                 2) Call waifu2x to upscale whatever images are in 'residual_to_upscale' folder

                 3) After waifu2x call is finished, delete whatever files were just upscaled 
                   (all the contents of 'residual_to_upscale')
                   (this is to prevent Waifu2x from re-upscaling the same image again)

                 4) Repeat this process until merge.py broadcasts that its job had finished.
                   (close w2x when all frames were 'merged')
                   (done via context.upscaler_running object variable)
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

            while self.context.upscaler_running:
                
                # don't mix up already upscaled/pending residual files
                move_files_dir(self.residual_images_dir, self.residual_for_upscale)

                # upscale stuff moved to residual_for_upscale
                subprocess.call(exec_command, shell=False, stderr=console_output, stdout=console_output)

                # delete residual_for_upscale for not re-upscaling in the future
                delete_dir_contents(self.residual_for_upscale)

                # calm down moving and calling subprocess!
                time.sleep(0.1)
