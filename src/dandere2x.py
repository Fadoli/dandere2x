#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Licensed under the GNU General Public License Version 3 (GNU GPL v3),
    available at: https://www.gnu.org/licenses/gpl-3.0.txt

(C) 2018-2019 aka_katto

Dandere2X is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Dandere2X is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Description: Dandere2X is an automation software based on waifu2x image
enlarging engine. It extracts frames from a video, enlarge it by a
number of times without losing any details or quality, keeping lines
smooth and edges sharp.
"""

import logging
import os
import shutil
import sys
import threading
import time
import json
import subprocess

from dandere2xlib.core.difference import difference_loop
from dandere2xlib.core.merge import merge_loop
from dandere2xlib.realtime_encoding import run_realtime_encoding
from dandere2xlib.status import print_status
from dandere2xlib.utils.dandere2x_utils import valid_input_resolution, get_a_valid_input_resolution
from dandere2xlib.utils.dandere2x_utils import file_exists, get_operating_system
from wrappers.dandere2x_cpp import Dandere2xCppWrapper
from wrappers.ffmpeg.ffmpeg import extract_frames, trim_video
from wrappers.frame.frame_compressor import compress_frames
from wrappers.waifu2x.waifu2x_caffe import Waifu2xCaffe
from wrappers.waifu2x.waifu2x_converter_cpp import Waifu2xConverterCpp
from wrappers.waifu2x.waifu2x_vulkan import Waifu2xVulkan
from wrappers.waifu2x.waifu2x_vulkan_linux import Waifu2xVulkanLinux


# [tremx] appending folders and sub folders to path

modules_dic_path = {
    "dandere2xlib": [
        "core", "utils"
    ],
    "wrappers": [
        "ffmpeg", "frame", "waifu2x"
    ]
}

ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) + os.path.sep

path_to_add = [ROOT_DIR]

for key in modules_dic_path:
    path_to_add.append(os.path.join(ROOT_DIR, key))

for key in modules_dic_path:
    for subdir in modules_dic_path[key]:
        path_to_add.append(os.path.join(ROOT_DIR, key, subdir))


for path in path_to_add:
    print("Adding to path:", path)
    sys.path.append(path)

# [tremx] done, might be callable in 
# a outside dir or at least that is the hope



## SEE IF A WAIFU2X VULKAN BINARY ANY GOOD
def check_w2x_vulkan():
    if "linux" in get_operating_system():
        with open("dandere2x_linux.json", "r") as f:
            data = json.load(f)
            if data["dandere2x"]["usersettings"]["waifu2x_type"] == "vulkan":
                vk = data["waifu2x_ncnn_vulkan"]
                binary = vk["waifu2x_ncnn_vulkan_file_name"]
                vkrootpath = vk["waifu2x_ncnn_vulkan_path"]

                selectvk = False

                if not os.path.isfile(os.path.join(vkrootpath, binary)):
                    selectvk = True
                
                if binary == "" or vkrootpath == "":
                    selectvk = True

                #if not configured a w2x vk binary inthe linux.json file:
                if selectvk:
                    w2xclass = subprocess.run(['whereis', 'waifu2x-ncnn-vulkan'], stdout=subprocess.PIPE).stdout.decode('utf-8')
                    #with this line we need Python >= 3.5

                    binaries = w2xclass.split(" ")[1:]

                    #Permission erros on /usr/share when running as a normal user
                    for i in range(len(binaries) - 1):
                        if "/usr/share" in binaries[i]:
                            del binaries[i]

                    print("\n\n !!IMPORTANT!! \n\n")
                    print("No waifu2x vulkan binary found based on the json config")
                    print("Please select (a found) one listed here on your system")
                    print("Or manually configure it in the dandere2x_linux.json file.\n")

                    for i in range(len(binaries)):
                        print("[" + str(i) + "]: ", binaries[i])

                    while True:
                        if len(binaries) > 1:
                            uinput = input("\nEnter the number of the desired binary: ")
                        else:
                            print("Only one binary found, will use it.")
                            uinput = 0

                        try:
                            uinput = int(uinput)
                            
                            if uinput > len(binaries) - 1:
                                print("You entered a number too high!")

                            elif uinput < 0:
                                print("You entered a number too low!")

                            else:
                                chosen = binaries[uinput]
                                print("\n You chose the binary:", chosen)

                                chosen = chosen.split("/")
                                
                                binfile = chosen[-1]
                                binpath = '/'.join(chosen[:-1]) + "/"

                                print("\nBinary: ", binfile)
                                print("Path: ", binpath)

                                print("Updating JSON Linux config\n")
                                
                                data["waifu2x_ncnn_vulkan"]["waifu2x_ncnn_vulkan_path"] = binpath
                                data["waifu2x_ncnn_vulkan"]["waifu2x_ncnn_vulkan_file_name"] = binfile

                                with open("dandere2x_linux.json", "w") as f2:
                                    json.dump(data, f2, indent=4)
                                
                                break

                        except ValueError:
                            print("That's not a int number!")
check_w2x_vulkan()



class Dandere2x:

    def __init__(self, context):
        self.context = context
        self.directories = None

    # This is the main driver for Dandere2x_Python.
    # Essentially we need to call a bunch of different
    # subprocesses to run concurrent with one another
    # To achieve maximum performance.

    def run_concurrent(self):

        # load context
        output_file = self.context.output_file


        # The first thing to do is create the dirs we will need during runtime
        self.create_dirs()
        self.context.set_logger()
        self.write_merge_commands()


        # If the user wishes to trim the video, trim the video,
        # then rename the file_dir to point to the trimmed video
        if self.context.user_trim_video:
            trimed_video = os.path.join(self.context.workspace, "trimmed.mkv")
            trim_video(self.context, trimed_video)
            self.context.input_file = trimed_video


        # Before we extract all the frames, we need to ensure
        # the settings are valid. If not, resize the video
        # To make the settings valid somehow.

        if not valid_input_resolution(self.context.width, self.context.height, self.context.block_size):
            self.append_video_resize_filter()


        # Extract all the frames
        print("extracting frames from video... this might take a while..")
        extract_frames(self.context, self.context.input_file)
        self.context.update_frame_count()


        # Assign the waifu2x object to whatever waifu2x we're using
        waifu2x = self.get_waifu2x_class(self.context.waifu2x_type)


        # Upscale the first file (the genesis file is treated different in Dandere2x)
        one_frame_time = time.time()  # This timer prints out how long it takes to upscale one frame


        upscale_input = self.context.input_frames_dir + "frame1" + self.context.extension_type
        upscale_output = self.context.merged_dir + "merged_1" + self.context.extension_type

        waifu2x.upscale_file(input_file=upscale_input, output_file=upscale_output)


        # Ensure the first file was able to get upscaled.
        # We literally cannot continue if it doesn't.

        if not file_exists(self.context.merged_dir + "merged_1" + self.context.extension_type):
            print("Could not upscale first file.. check logs file to see what's wrong")
            logging.info("Could not upscale first file.. check logs file to see what's wrong")
            logging.info("Exiting Dandere2x...")
            sys.exit(1)

        print("\n Time to upscale an uncompressed frame: ",
              str(round(time.time() - one_frame_time, 2)))

        # This is where Dandere2x's core functions start.
        # Each core function is divided into a series of threads,
        # All with their own segregated tasks and goals.
        # Dandere2x starts all the threads, and lets it go from there.

        # creating the threads into a list
        threads = []
        threads.append(waifu2x)
        threads.append(threading.Thread(target=merge_loop, args=(self.context, 1)))
        threads.append(threading.Thread(target=difference_loop, args=(self.context, 1)))
        threads.append(Dandere2xCppWrapper(self.context, resume=False))
        threads.append(threading.Thread(target=print_status, args=(self.context,)))
        threads.append(threading.Thread(target=compress_frames, args=(self.context,)))

        if self.context.realtime_encoding_enabled:
            threads.append(
                threading.Thread(target=run_realtime_encoding, args=(self.context, output_file))
                )

        logging.info("starting new d2x process")

        # starting the threads
        for thread in threads:
            thread.start()

        # waiting for them to finish
        for thread in threads:
            thread.join()

        self.context.logger.info("Threaded Processes Finished succcesfully")





    # Resume a Dandere2x Session
    # Consider merging this into one function, but for the time being I prefer it seperate
    # to-do this this work?

    def resume_concurrent(self): # resume functions doesn't really work as said by aka, I'll not break my mind in them

        # we need to count how many outputs there are after ffmpeg extracted stuff
        self.context.update_frame_count()
        self.context.set_logger()

        if self.context.realtime_encoding_delete_files:
            print("CANNOT RESUME RUN ON DELETE FILES TYPED SESSION")
            sys.exit(1)

        if self.context.user_trim_video:
            trimed_video = os.path.join(self.context.workspace, "trimmed.mkv")
            self.context.input_file = trimed_video

        # get whatever waifu2x class we're using
        waifu2x = self.get_waifu2x_class(self.context.waifu2x_type)

        threads = []

        threads.append(waifu2x)
        threads.append(threading.Thread(target=merge_loop, args=(self.context, 1)))
        threads.append(threading.Thread(target=difference_loop, args=(self.context, 1)))
        threads.append(Dandere2xCppWrapper(self.context, resume=False))
        threads.append(threading.Thread(target=print_status, args=(self.context,)))
        threads.append(threading.Thread(target=compress_frames, args=(self.context,)))

        if self.context.realtime_encoding == 1:
            output_file = self.context.workspace + 'output.mkv'
            threads.append(threading.Thread(target=run_realtime_encoding,
                                            args=(self.context, output_file)))

        self.context.logger.info("Starting Threaded Processes..")

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        self.context.logger.info("Threaded Processes Finished successfully")


    # We could just get the name from self.context, but for readibility it's easier to know
    # What the function does based off what it's passed.
    def get_waifu2x_class(self, name: str):
        if name == "caffe":
            return Waifu2xCaffe(self.context)

        if name == "converter_cpp":
            return Waifu2xConverterCpp(self.context)

        # for the time being linux and vulkan have seperate classes
        if name == "vulkan": 
            
            if "linux" in get_operating_system():
            
                #loading d2x.json
                with open("dandere2x_linux.json", "r") as f:
                    data = json.load(f)
                    vk = data["waifu2x_ncnn_vulkan"]
                    vkrootpath = vk["waifu2x_ncnn_vulkan_path"]

                    msg = ("   >> Even though the two have the same binary name\n"
                        "   >> The two are not interchangeable internally\n"
                        "   >> If you see errors about bad command usage in the log\n"
                        "   >> Make sure you have a correct JSON first\n"
                        "   >> Then see if it's using the right version of w2x-vulkan\n"
                        "   >> The versions are determined by if in the path the word 'snap' is present.\n\n"
                        "Extracting frames from video... This might take a while..")

                    #check if it's snap or not. could be system agnostic, not sure
                    #and then pick the right w2x process to use

                    if not "snap" in vkrootpath:
                        print("\n We're not using waifu2x-ncnn-vulkan from Snap!!\n")
                        print(msg)

                        return Waifu2xVulkan(self.context)

                    else:
                        print("\n We're using waifu2x-ncnn-vulkan from Snap!!\n")
                        print(msg)

                        return Waifu2xVulkanLinux(self.context)

            elif "win" in get_operating_system():
                return Waifu2xVulkan(self.context)

            

        logging.info("no valid waifu2x selected")
        print("no valid waifu2x selected")
        exit(1)
        return 0


    def append_video_resize_filter(self):
        print("Forcing Resizing to match blocksize..")
        width, height = get_a_valid_input_resolution(self.context.width,
                                                     self.context.height,
                                                     self.context.block_size)

        print("New width -> " + str(width))
        print("New height -> " + str(height))

        self.context.width = width
        self.context.height = height

        self.context.config_json['ffmpeg']['video_to_frames']['output_options']['-vf'] \
            .append("scale=" + str(self.context.width) + ":" + str(self.context.height))


    def difference_only(self):
        dandere2xcpp_thread = Dandere2xCppWrapper(self.context, resume=False)
        difference_thread = threading.Thread(target=difference_loop, args=(self.context, 1))

        self.context.logger.info("Starting Threaded Processes..")

        difference_thread.start()
        dandere2xcpp_thread.start()

        dandere2xcpp_thread.join()
        difference_thread.join()


    def merge_only(self):
        threading.Thread(target=merge_loop, args=(self.context, 1)).start().join()


    # delete every folder except the log file in the workspace
    # This because the log file doesn't want to get deleted + having the log
    # stay alive even after everything finishes is useful to know
    def delete_workspace_files(self):
        """
        [tremx] docstring here also :D
        """

        # create each directory
        for subdirectory in self.directories:
            try:
                shutil.rmtree(subdirectory)
            except OSError:
                print("Deletion of the directory %s failed" % subdirectory)
            else:
                print("Successfully deleted the directory %s " % subdirectory)

        no_sound = os.path.join(self.context.workspace, "nosound.mkv")

        try:
            os.remove(no_sound)

        except OSError:
            print("Deletion of the file %s failed" % no_sound)
            print(OSError.strerror)
        else:
            print("Successfully deleted the file %s " % no_sound)

    def create_dirs(self):
        # create a list of directories we need to create
        self.directories = {self.context.input_frames_dir,
                            self.context.correction_data_dir,
                            self.context.differences_dir,
                            self.context.upscaled_dir,
                            self.context.merged_dir,
                            self.context.upscaled_dir,
                            self.context.merged_dir,
                            self.context.inversion_data_dir,
                            self.context.pframe_data_dir,
                            self.context.debug_dir,
                            self.context.log_dir,
                            self.context.compressed_static_dir,
                            self.context.compressed_moving_dir,
                            self.context.fade_data_dir,
                            self.context.encoded_dir,
                            self.context.temp_image_folder}

        # need to create workspace before anything else
        try:
            os.mkdir(self.context.workspace)
        except OSError:
            print("Creation of the directory %s failed, already exists?" % self.context.workspace)
        else:
            print("Successfully created the directory %s " % self.context.workspace)

        # create each directory
        for subdirectory in self.directories:
            try:
                os.mkdir(subdirectory)
                print("Successfully created the directory %s " % subdirectory)

            except OSError:
                print("Creation of the directory %s failed, already exists?" % subdirectory)
                

    # This is almost legacy code and is being left in for
    # A very small demographic of people who want to manually encode the video after runtime

    def write_merge_commands(self):

        no_audio_video = self.context.workspace + "nosound.mkv"
        finished_video = self.context.workspace + "finished.mkv"

        merged_frames = self.context.merged_dir + "merged_%d.jpg"


        migrate_tracks_command = ("[ffmpeg_dir] -i [no_audio] -i [file_dir] -t 00:00:10"
                                  " -map 0:v:0 -map 1? -c copy -map -1:v? [output_file]")

        video_from_frames_command = ("[ffmpeg_dir] -loglevel 0 -nostats -framerate [frame_rate]"
                                     " -start_number [start_number] -i [input_frames] -vframes"
                                     " [end_number] -vf deband=blur=false:range=22 [output_file]")


        migrate_replace = {
            "[ffmpeg_dir]": self.context.ffmpeg_dir,
            "[no_audio]": no_audio_video,
            "[file_dir]": self.context.input_file,
            "[output_file]": finished_video
        }

        video_replace = {
            "[ffmpeg_dir]": self.context.ffmpeg_dir,
            "[frame_rate]": str(self.context.frame_rate),
            "[start_number]": str(0),
            "[input_frames]": merged_frames,
            "[end_number]": "",
            "-vframes": "",
            "[output_file]": no_audio_video
        }

        for change in migrate_replace:
            migrate_tracks_command = migrate_tracks_command.replace(change, migrate_replace[change])

        for change in video_replace:
            video_from_frames_command = video_from_frames_command.replace(change, video_replace[change])

        with open(self.context.workspace + os.path.sep + 'commands.txt', 'w') as f:
            f.write(video_from_frames_command + "\n")
            f.write(migrate_tracks_command + "\n")
