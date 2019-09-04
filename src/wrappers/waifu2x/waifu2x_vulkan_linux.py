#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Name: Dandere2X waifu2x-vulkan)
Author: CardinalPanda
Date Created: March 22, 2019
Last Modified: April 2, 2019

Description: # A pretty hacky wrapper for Waifu2x-Vulkan
Behaves pretty similar to waifu2x-caffe, except directory must be
set  (for subprocess call, waifu2x_vulkan_dir_dir keeps this variable) and arguments are slightly different.
Furthermore, waifu2x-vulkan saves files in an annoying way, i.e it becomes image.png.png when saving in batches.
so we need to correct those odd namings.
"""

import copy
import logging
import os
import subprocess
import threading

from context import Context
from dandere2xlib.utils.dandere2x_utils import file_exists, get_lexicon_value, rename_file, wait_on_either_file, wait_on_file
from dandere2xlib.utils.json_utils import get_options_from_section


class Waifu2xVulkanLinux(threading.Thread):
    def __init__(self, context: Context):
        # load context
        self.frame_count = context.frame_count
        self.waifu2x_ncnn_vulkan_file_path = context.waifu2x_ncnn_vulkan_file_path
        self.waifu2x_vulkan_path = context.waifu2x_ncnn_vulkan_path
        self.differences_dir = context.differences_dir
        self.upscaled_dir = context.upscaled_dir
        self.noise_level = context.noise_level
        self.scale_factor = context.scale_factor
        self.workspace = context.workspace
        self.context = context

        self.waifu2x_vulkan_upscale_frame = [self.waifu2x_ncnn_vulkan_file_path,
                                             "[input_file]",
                                             "[output_file]",
                                             str(self.noise_level),
                                             str(self.scale_factor),
                                             str(200)]

        # waifu2x_vulkan_options = get_options_from_section(
        #     self.context.config_json["waifu2x_ncnn_vulkan"]["output_options"])
        #
        # # add custom options to waifu2x_vulkan
        # for element in waifu2x_vulkan_options:
        #     self.waifu2x_vulkan_upscale_frame.append(element)
        #
        # self.waifu2x_vulkan_upscale_frame.extend(["-o", "[output_file]"])

        threading.Thread.__init__(self)
        logging.basicConfig(filename=self.workspace + 'waifu2x.log', level=logging.INFO)

    # manually upscale a single file
    def upscale_file(self, input_file: str, output_file: str):
        # load context
        waifu2x_vulkan_dir_dir = self.context.waifu2x_ncnn_vulkan_path
        d2x_exec = copy.copy(self.waifu2x_vulkan_upscale_frame)
        logger = logging.getLogger(__name__)

        # replace the d2x_exec command withthe files we're concerned with
        for x in range(len(d2x_exec)):
            if d2x_exec[x] == "[input_file]":
                d2x_exec[x] = input_file

            if d2x_exec[x] == "[output_file]":
                d2x_exec[x] = output_file

        logger.info("Vulkan Exec")
        logger.info(str(d2x_exec))

        logger.info("Changind Dirs")
        logger.info(str(waifu2x_vulkan_dir_dir))

        os.chdir(waifu2x_vulkan_dir_dir)

        logger.info("manually upscaling file")
        logger.info(d2x_exec)

        console_output = open(self.context.log_dir + "vulkan_upscale_frame.txt", "w")
        console_output.write(str(d2x_exec))
        subprocess.call(d2x_exec, shell=False, stderr=console_output, stdout=console_output)
        console_output.close()

    # Waifu2x-Converter-Cpp adds this ugly '[NS-L3][x2.000000]' to files, so
    # this function just renames the files so Dandere2x can interpret them correctly.
    def fix_names(self):

        list_of_names = os.listdir(self.upscaled_dir)
        for name in list_of_names:
            if '.jpg.jpg' in name:
                rename_file(self.upscaled_dir + name,
                            self.upscaled_dir + name.replace('.jpg.png', '.png'))

    # This function is tricky. Essentially we do multiple things in one function
    # Because of 'gotchas'

    # First, we make a list of prefixes. Both the desired file name and the produced file name
    # Will start with the same prefix (i.e all the stuff in file_names).

    # Then, we have to specify what the dirty name will end in. in Vulkan's case, it'll have a ".png.png"
    # We then have to do a try / except to try to rename it back to it's clean name, since it may still be
    # being written / used by another program and not safe to edit yet.
    def fix_names_all(self):

        file_names = []
        for x in range(1, self.frame_count):
            file_names.append("output_" + get_lexicon_value(6, x))

        for file in file_names:
            dirty_name = self.upscaled_dir + file + ".jpg.png"
            clean_name = self.upscaled_dir + file + ".png"

            wait_on_either_file(clean_name, dirty_name)

            if file_exists(clean_name):
                pass

            elif file_exists(dirty_name):
                while file_exists(dirty_name):
                    try:
                        rename_file(dirty_name, clean_name)
                    except PermissionError:
                        pass

    # (description from waifu2x_caffe)
    # The current Dandere2x implementation requires files to be removed from the folder
    # During runtime. As files produced by Dandere2x don't all exist during the initial
    # Waifu2x call, various work arounds are in place to allow Dandere2x and Waifu2x to work in real time.

    # Briefly, 1) Create a list of names that will be upscaled by waifu2x,
    #          2) Call waifu2x to upscale whatever images are in 'differences' folder
    #          3) After waifu2x call is finished, delete whatever files were upscaled, and remove those names from list.
    #             (this is to prevent Waifu2x from re-upscaling the same image again)
    #          4) Repeat this process until all the names are removed.
    def run(self):
        logger = logging.getLogger(__name__)

        differences_dir = self.context.differences_dir
        upscaled_dir = self.context.upscaled_dir
        d2x_exec = copy.copy(self.waifu2x_vulkan_upscale_frame)

        for x in range(1, self.frame_count):
            wait_on_file(differences_dir + "output_" + get_lexicon_value(6, x) + ".jpg")

            self.upscale_file(differences_dir + "output_" + get_lexicon_value(6, x) + ".jpg",
                              upscaled_dir + "output_" + get_lexicon_value(6, x) + ".png")

            #wait_on_file(upscaled_dir + "output_" + get_lexicon_value(6, x) + ".png")

