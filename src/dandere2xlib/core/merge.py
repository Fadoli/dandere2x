#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import threading
import logging
import time
import os

from PIL import Image
from context import Context
from dandere2xlib.core.plugins.correction import correct_image
from dandere2xlib.core.plugins.fade import fade_image
from dandere2xlib.core.plugins.pframe import pframe_image
from dandere2xlib.utils.dandere2x_utils import get_lexicon_value, get_list_from_file, wait_on_file, remove_file_wait
from wrappers.ffmpeg.ffmpeg import migrate_tracks
from wrappers.frame.asyncframe import AsyncFrameWrite, AsyncFrameRead
from wrappers.frame.frame import Frame






class PiperSaverDeleter():

    def __init__(self, context):    
        self.context = context
            
            # load variables from context
        
        self.workspace = self.context.workspace
        self.upscaled_dir = self.context.residual_upscaled_dir
        self.compressed_static_dir = self.context.compressed_static_dir
        self.compressed_moving_dir = self.context.compressed_moving_dir
        self.input_frames_dir = self.context.input_frames_dir
        self.merged_dir = self.context.merged_dir
        self.residual_data_dir = self.context.residual_data_dir
        self.pframe_data_dir = self.context.pframe_data_dir
        self.correction_data_dir = self.context.correction_data_dir
        self.fade_data_dir = self.context.fade_data_dir
        self.frame_count = self.context.frame_count
        self.extension_type = self.context.extension_type
        self.ffmpeg_pipe_encoding = self.context.ffmpeg_pipe_encoding
        self.realtime_encoding_enabled = self.context.realtime_encoding_enabled
        self.waifu2x_type = self.context.waifu2x_type

        if self.ffmpeg_pipe_encoding:
            self.setup_ffmpeg_pipe_encode()

    
    def setup_ffmpeg_pipe_encode(self):

        self.pipe_running = 1
        self.images_to_pipe = []
        
        self.nosound_file = self.context.nosound_file
        self.frame_rate = str(self.context.frame_rate)
        self.input_file = self.context.input_file
        self.output_file = self.context.output_file
        self.ffmpeg_dir = self.context.ffmpeg_dir
        self.ffmpeg_pipe_encoding_type = self.context.ffmpeg_pipe_encoding_type

        # ffmpeg muxer / demuxer options

        # video out
        if ".mkv" in self.nosound_file:
            self.flag_format = "matroska"

        elif ".mp4" in self.nosound_file:
            self.flag_format = "mp4"
        
        else: # defaults to mkv
            self.flag_format = "matroska"

        
        # pipe format and codec "read"
        if self.ffmpeg_pipe_encoding_type in ["jpeg", "jpg"]:
            self.vcodec = "mjpeg"
            self.pipe_format = "JPEG"

        elif self.ffmpeg_pipe_encoding_type == "png":
            self.vcodec = "png"
            self.pipe_format = "PNG"

        else: # and defaults to jpeg
            print("  Error: no valid ffmpeg_pipe_encoding_type set. Using jpeg as default")
            self.vcodec = "mjpeg"
            self.pipe_format = "JPEG"

        print("\n    WARNING: EXPERIMENTAL FFMPEG PIPING IS ENABLED\n")

        self.ffmpeg_pipe_command = [self.ffmpeg_dir,
                                    "-loglevel", "panic",
                                    '-y', '-f', 'image2pipe',
                                    #'-rtbufsize', '15M',
                                    #'-fflags', 'nobuffer',
                                    '-vcodec', self.vcodec, 
                                    '-r', self.frame_rate, 
                                    '-i', '-',
                                    '-q:v', '2',
                                    #'-fflags', 'nobuffer',
                                    #'-vcodec', 'libx264', # 3, 4, 5 GBs of RAM roflmao
                                    # '-c:v', 'libvpx-vp9', # don't pass 1 GB, dead compression
                                    '-c:v', 'libxvid',
                                    #'-rtbufsize', '15M',
                                    #'-bufsize', '15M',
                                    '-preset', 'fast',
                                    '-qscale:v', '6', # 1 (best) - 31 (worst)
                                    #'-crf', '17', #only for h264
                                    "-f", self.flag_format,
                                    '-vf', ' pp=hb/vb/dr/fq|32, deband=range=22:blur=false',
                                    '-r', self.frame_rate, 
                                    self.nosound_file]

        self.ffmpeg_pipe_subprocess = subprocess.Popen(self.ffmpeg_pipe_command, stdin=subprocess.PIPE)

        # pipe the first merged image as it will not be done afterwards
        wait_on_file(self.merged_dir + "merged_1" + self.extension_type)
        im = Image.open(self.merged_dir + "merged_1" + self.extension_type)

        # best jpeg quality since we won't be saving up disk space
        im.save(self.ffmpeg_pipe_subprocess.stdin, format=self.pipe_format, quality=95)

        threading.Thread(target=self.write_to_pipe).start()


    def write_to_pipe(self):
        while self.pipe_running:
            if len(self.images_to_pipe) > 0:
                img = self.images_to_pipe.pop(0).get_pil_image() # get the first image and remove it from list
                img.save(self.ffmpeg_pipe_subprocess.stdin, format=self.pipe_format, quality=95)
            time.sleep(0.05)

        # close and finish audio file

        print("\n  Closing FFMPEG as encode finished")
        
        self.ffmpeg_pipe_subprocess.stdin.close()
        self.ffmpeg_pipe_subprocess.wait()
        
        # add the original file audio to the nosound file
        migrate_tracks(self.context, self.nosound_file,
                       self.input_file, self.output_file)

        print("\n  Finished!!")


    def add_to_pipe(self, img):
        # add image to image_to_pipe list
        # kinda similar to AsyncFrameWrite
        # Write the image directly into ffmpeg pipe
        while True:
            if len(self.images_to_pipe) < 10: # buffer limit
                self.images_to_pipe.append(img)
                break
            time.sleep(0.05)

    def async_saver(self, img, x):
        # Write the image in the background for the preformance increase
        output_file_merged = self.merged_dir + "merged_" + str(x + 1) + self.extension_type
        background_frame_write = AsyncFrameWrite(img, output_file_merged)
        background_frame_write.start()


    def save(self, frame, x):
        if self.ffmpeg_pipe_encoding:
            #ffmpeg piping is enabled
            self.add_to_pipe(frame)
        else:
            # ffmpeg piping is disabled, traditional way
            self.async_saver(frame, x)


    
    def make_frame_next(self, ind, f1_arg, frame_previous_arg):
        prediction_data_file = self.pframe_data_dir + "pframe_" + str(ind) + ".txt"
        residual_data_file = self.residual_data_dir + "residual_" + str(ind) + ".txt"
        correction_data_file = self.correction_data_dir + "correction_" + str(ind) + ".txt"
        fade_data_file = self.fade_data_dir + "fade_" + str(ind) + ".txt"

        prediction_data_list = get_list_from_file(prediction_data_file)
        residual_data_list = get_list_from_file(residual_data_file)
        correction_data_list = get_list_from_file(correction_data_file)
        fade_data_list = get_list_from_file(fade_data_file)

        merged = make_merge_image(self.context, f1_arg, frame_previous_arg,
                                  prediction_data_list, residual_data_list,
                                  correction_data_list, fade_data_list)

        return merged

    
    def delete_used_files(self, remove_before):
        """
        Two main things:

        Call next frame and remove the already used ones only
        if the minimal-disk setting is enabled on the config

        Delete the "already used" files (always index_to_remove behind)

        This way we clean the workspace as we're moving on with the encode
        """

        # get the files to delete "_r(emove)"

        index_to_remove = str(remove_before - 2)

        prediction_data_file_r = self.pframe_data_dir + "pframe_" + index_to_remove + ".txt"
        residual_data_file_r = self.residual_data_dir + "residual_" + index_to_remove + ".txt"
        correction_data_file_r = self.correction_data_dir + "correction_" + index_to_remove + ".txt"
        fade_data_file_r = self.fade_data_dir + "fade_" + index_to_remove + ".txt"

        input_image_r = self.input_frames_dir + "frame" + index_to_remove + ".jpg"
        
        compressed_file_static_r = self.compressed_static_dir + "compressed_" + index_to_remove + ".jpg"
        compressed_file_moving_r = self.compressed_moving_dir + "compressed_" + index_to_remove + ".jpg"
        
        # "mark" them
        remove = [prediction_data_file_r, residual_data_file_r, correction_data_file_r,
                  fade_data_file_r, input_image_r, #upscaled_file_r,
                  compressed_file_static_r, compressed_file_moving_r]
    
        if self.waifu2x_type == "vulkan":
            upscaled_file_r = self.upscaled_dir + "output_" + get_lexicon_value(6, int(remove_before)) + ".png"
            remove.append(upscaled_file_r)

        # remove
        threading.Thread(target=self.remove_unused_list, args=(remove,), daemon=True).start()


    def remove_unused_list(self, files):
        for item in files:
            c = 0
            while True:
                if os.path.isfile(item):
                    try:
                        os.remove(item)
                        break
                    except OSError:
                        c += 1
                else:
                    c += 1
                if c == 20:
                    break
                time.sleep(0.1)
    
    def finish(self):
        if self.ffmpeg_pipe_encoding:
            print("    Waiting the ffmpeg-pipe-encode buffer list..")

            while self.images_to_pipe:
                time.sleep(0.05)

            self.pipe_running = 0



def merge_loop(context: Context, d2x_main, PFEOBJ = None):
    """
    Call the 'make_merge_image' method for every image that needs to be upscaled.

    This method is sort of the driver for that, and has tasks needed to keep merging running smoothly.

    This method became a bit messy due to optimization-hunting, but the most important calls of the loop can be read in
    the 'Loop-iteration Core' area.

    Method Tasks:

        - Read / Write files that are used by merge asynchronously.
        - Load the text files containing the vectors needed for 'make_merge_image'

    """

    corelogic = PiperSaverDeleter(context)

    logger = logging.getLogger(__name__)

    # Progressive Frames Extractor (PFE) stuff
    if PFEOBJ == None:
        PFE_enabled = False
    else:
        PFE_enabled = True

    # Load the genesis image + the first upscaled image.
    frame_previous = Frame()
    frame_previous.load_from_string_wait(context.merged_dir + "merged_" + str(1) + context.extension_type)

    f1 = Frame()
    f1.load_from_string_wait(context.residual_upscaled_dir + "output_" + get_lexicon_value(6, 1) + ".png")

    # When upscaling every frame between start_frame to frame_count, there's obviously no x + 1 at frame_count - 1 .
    # So just make a small note not to load that image. Pretty much load images concurrently until we get to x - 1
    last_frame = False
    frame_count = context.frame_count

    for x in range(1, frame_count):

        #print("new index", x)
        
        ###################################
        # Loop-iteration pre-requirements #
        ###################################

        # Check if we're at the last image
        if x >= frame_count - 1:
            last_frame = True

        # load the next image ahead of time.
        if not last_frame:
            background_frame_load = AsyncFrameRead((context.residual_upscaled_dir + "output_" + 
                                                    get_lexicon_value(6, x + 1) + ".png"))
            background_frame_load.start()


        #######################
        # Loop-iteration Core #
        #######################


        logger.info("Upscaling frame " + str(x))

        frame_next = corelogic.make_frame_next(x, f1, frame_previous)

        if PFE_enabled:
            corelogic.delete_used_files(x)
            PFEOBJ.next_frame()

        corelogic.save(frame_next, x)


        #######################################
        # Assign variables for next iteration #
        #######################################
        

        if not last_frame:
            while not background_frame_load.load_complete:
                time.sleep(.5)
                #wait_on_file(upscaled_dir + "output_" + get_lexicon_value(6, x + 1) + ".png")

            f1 = background_frame_load.loaded_image

        frame_previous = frame_next

        # Ensure the file is loaded for background_frame_load. If we're on the last frame, simply ignore this section
        # Because the frame_count + 1 does not exist.

    d2x_main.stop_upscaler = True
    corelogic.finish()
    



def make_merge_image(context: Context, frame_residual: Frame, frame_previous: Frame,
                     list_predictive: list, list_residual: list, list_corrections: list, list_fade: list):
    """
    This section can best be explained through pictures. A visual way of expressing what 'merging'
    is doing is this section in the wiki.

    https://github.com/aka-katto/dandere2x/wiki/How-Dandere2x-Works#part-2-using-observations-to-save-time

    Inputs:
        - frame(x)
        - frame(x+1)_residual
        - Residual vectors mapping frame(x+1)_residual -> frame(x+1)
        - Predictive vectors mapping frame(x) -> frame(x+1)

    Output:
        - frame(x+1)
    """

    # Load context
    logger = logging.getLogger(__name__)

    out_image = Frame()
    out_image.create_new(frame_previous.width, frame_previous.height)

    # If list_predictive and list_predictive are both empty, then the residual frame
    # is simply the new image.
    if not list_predictive and not list_predictive:
        out_image.copy_image(frame_residual)
        return out_image

    # by copying the image first as the first step, all the predictive elements like
    # (0,0) -> (0,0) are also coppied
    out_image.copy_image(frame_previous)
    
    # run the image through the same plugins IN ORDER it was ran in d2x_cpp
    out_image = pframe_image(context, out_image, frame_previous, frame_residual, list_residual, list_predictive)
    out_image = fade_image(context, out_image, list_fade)
    out_image = correct_image(context, out_image, list_corrections)

    return out_image


# For debugging
def main():
    pass


if __name__ == "__main__":
    main()
