#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Name: Dandere2X Utils
Author: CardinalPanda
Date Created: March 22, 2019
Last Modified: April 2, 2019
"""

import logging
import os
import time
from sys import platform


def get_operating_system():
    if platform == "linux" or platform == "linux2":
        return 'linux'
    elif platform == "win32":
        return 'win32'

# if the value in the key value pair exists, add it.
# if the key is just 'true', only add the key

# THis doesnt work with multiple keys and import warnings



# tremx felt like adding a separator option because
# the one line per vector coordinate on the pframes files
# were activating my tingles so hard so I separated them into ","

# returns a list given a text file (representing a string) separated by a separator
def get_list_from_file(text_file: str, separator = "\n"):
    logger = logging.getLogger(__name__)
    exists = exists = os.path.isfile(text_file)
    count = 0
    while not exists:
        if count % 10000 == 0:
            logger.info(text_file + "dne, waiting")
        exists = os.path.isfile(text_file)
        count += 1
        time.sleep(.01)

    topenfile = None
    try:
        topenfile = open(text_file, "r")
    except PermissionError:
        logging.info("permission error on file" + text_file)

    while not topenfile:
        try:
            topenfile = open(text_file, "r")
        except PermissionError:
            logging.info("permission error on file" + text_file)

    text_list = topenfile.read().split(separator)
    topenfile.close()

    if len(text_list) == 1:
        return []

    return text_list


# many times a file may not exist yet, so just have this function
# wait if it does not.
def wait_on_file(file_string: str):
    logger = logging.getLogger(__name__)
    exists = os.path.isfile(file_string)
    count = 0
    while not exists:
        if count / 500 == 0:
            logger.info(file_string + "done, waiting")
            print("Waiting on file for more than .5s:", file_string)
            
        #[tremx] 10000000000000 too much bruh
        #lets just watch what file is wanted for more than .5 sec and only one time
        #if count % 1000000 == 0:
        #    logger.info(file_string + "dne, waiting")
        exists = os.path.isfile(file_string)
        count += 1
        time.sleep(.001)


# for renaming function, break when either file exists
def wait_on_either_file(file_1: str, file_2: str):
    logger = logging.getLogger(__name__)
    exists_1 = os.path.isfile(file_1)
    exists_2 = os.path.isfile(file_2)
    count = 0
    while not (exists_1 or exists_2):
        #[tremx] same here
        #if count % 1000000 == 0:
        #    logger.info(file_1 + "dne, waiting")

        if count / 500 == 0:
            logger.info(file_1 + "done, waiting")

        exists_1 = os.path.isfile(file_1)
        exists_2 = os.path.isfile(file_2)

        count += 1
        time.sleep(.001)


# Sometimes dandere2x is offsync with window's handlers, and a directory might be deleted after
# the call was made, so in some cases make sure it's completely deleted before moving on during runtime
def wait_on_delete_dir(dir: str):
    logger = logging.getLogger(__name__)
    exists = dir_exists(dir)
    count = 0
    while exists:
        if count / 500 == 0:
            logger.info(dir + "dne, waiting")
        exists = os.path.isfile(dir)
        count += 1
        time.sleep(.001)


# many times a file may not exist yet, so just have this function
# wait if it does not.
def file_exists(file_string: str):
    return os.path.isfile(file_string)


def dir_exists(file_string: str):
    return os.path.isdir(file_string)


# custom function to rename file if it already exists
def rename_file(file1, file2):
    try:
        os.rename(file1, file2)
    except FileExistsError:
        os.remove(file2)
        os.rename(file1, file2)


# Both waifu2x-Caffe and waifu2x-conv read images in lexiconic order, so in order
# to maximize efficiency, save the images that will be upscaled by waifu2x in lexiconic ordering.
def get_lexicon_value(digits: int, val: int):
    return str(val).zfill(digits) #tremx was angry with the old mess


# get frame count from a string input
def get_seconds_from_time(time_frame: int):
    splitted = time_frame.split(":")
    print(splitted)
    hours_seconds = int(splitted[0]) * 3600
    minutes_seconds = int(splitted[1]) * 60
    seconds = int(splitted[2])

    return hours_seconds + minutes_seconds + seconds


def get_valid_block_sizes(width: int, height: int, minimum=1):
    valid_sizes = []

    larger_val = [width, height][height > width]

    for x in range(minimum, larger_val):
        if width % x == 0 and height % x == 0:
            valid_sizes.append(str(x))

    return valid_sizes


def valid_input_resolution(width: int, height: int, block_size: int):
    return width % block_size == 0 and height % block_size == 0


def get_a_valid_input_resolution(width: int, height: int, block_size: int):
    width_up = width
    width_down = width

    height_up = height
    height_down = height

    while width_up % block_size != 0:
        width_up = width_up + 1

    while width_down % block_size != 0:
        width_down = width_down - 1

    while height_up % block_size != 0:
        height_up = height_up + 1

    while height_down % block_size != 0:
        height_down = height_down - 1

    smaller_width = width_up if abs(width_up - width) < abs(width_down - width) else width_down

    smaller_height = height_up if abs(height_up - height) < abs(height_down - height) else height_down

    return smaller_width, smaller_height


# TODO bring this to ffprobe's modern settings
# TODO Very outdated!
# load the first frame, check if the block size is compatible with the resolution
def verify_user_settings(context):
    from wrappers.frame.frame import Frame

    input_frames_dir = context.input_frames_dir
    extension_type = context.extension_type
    block_size = context.block_size

    f1 = Frame()
    f1.load_from_string(input_frames_dir + "frame1" + extension_type)

    if f1.width % block_size != 0 and f1.height % block_size != 0:
        print("----------------------ERROR---------------------------------------")
        print("Your block size is incompatible with the resolution you provided. ")
        print("Valid Block sizes are:")
        print("------------------------------------------------------------------")
        valid_sizes = []

        larger_val = [f1.width, f1.height][f1.height > f1.width]

        for x in range(1, larger_val):
            if f1.width % x == 0 and f1.height % x == 0:
                valid_sizes.append(x)

        print(valid_sizes)
        print("------------------------------------------------------------------")
        new_block_size = int(input("Enter your value (recommended 25 or greater): "))

        while new_block_size not in valid_sizes:
            new_block_size = int(input("Invalid Choice! Re-Enter a correct value: "))

        context.block_size = new_block_size
