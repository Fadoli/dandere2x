#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
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

PFE_enabled = None

def merge_loop(context: Context, PFEOBJ = None):
    """
    Call the 'make_merge_image' method for every image that needs to be upscaled.

    This method is sort of the driver for that, and has tasks needed to keep merging running smoothly.

    This method became a bit messy due to optimization-hunting, but the most important calls of the loop can be read in
    the 'Loop-iteration Core' area.

    Method Tasks:

        - Read / Write files that are used by merge asynchronously.
        - Load the text files containing the vectors needed for 'make_merge_image'

    """

    global PFE_enabled

    # load variables from context
    workspace = context.workspace
    upscaled_dir = context.residual_upscaled_dir
    compressed_static_dir = context.compressed_static_dir
    compressed_moving_dir = context.compressed_moving_dir
    input_frames_dir = context.input_frames_dir
    merged_dir = context.merged_dir
    residual_data_dir = context.residual_data_dir
    residual_images_dir = context.residual_images_dir
    pframe_data_dir = context.pframe_data_dir
    correction_data_dir = context.correction_data_dir
    fade_data_dir = context.fade_data_dir
    frame_count = context.frame_count
    extension_type = context.extension_type
    logger = logging.getLogger(__name__)

    # # #  ffmpeg piping stuff  # # #

    ffmpeg_pipe_encoding = context.ffmpeg_pipe_encoding

    if ffmpeg_pipe_encoding:
        nosound_file = context.nosound_file
        frame_rate = str(context.frame_rate)
        input_file = context.input_file
        output_file = context.output_file
        ffmpeg_dir = context.ffmpeg_dir
        ffmpeg_pipe_encoding_type = context.ffmpeg_pipe_encoding_type

        # ffmpeg muxer / demuxer options

        # video out
        if ".mkv" in nosound_file:
            flag_format = "matroska"

        elif ".mp4" in nosound_file:
            flag_format = "mp4"
        
        else: # defaults to mkv
            flag_format = "matroska"
        
        # # #  # # #  # # #  # # #  # # #
        
        # pipe format and codec "read"
        if ffmpeg_pipe_encoding_type in ["jpeg", "jpg"]:
            vcodec = "mjpeg"
            pipe_format = "JPEG"

        elif ffmpeg_pipe_encoding_type == "png":
            vcodec = "png"
            pipe_format = "PNG"

        else: # and defaults to jpeg
            print("  Error: no valid ffmpeg_pipe_encoding_type set. Using jpeg as default")
            vcodec = "mjpeg"
            pipe_format = "JPEG"

        print("\n    WARNING: EXPERIMENTAL FFMPEG PIPING IS ENABLED\n")

        ffmpeg_pipe_command = [ffmpeg_dir,
                               "-loglevel", "panic",
                               '-y', '-f', 'image2pipe',
                               #'-rtbufsize', '15M',
                               #'-fflags', 'nobuffer',
                               '-vcodec', vcodec, 
                               '-r', frame_rate, 
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
                               "-f", flag_format,
                               '-vf', ' pp=hb/vb/dr/fq|32, deband=range=22:blur=false',
                               '-r', frame_rate, 
                               nosound_file]

        ffmpeg_pipe_subprocess = subprocess.Popen(ffmpeg_pipe_command, stdin=subprocess.PIPE)

        # pipe the first merged image as it will not be done afterwards
        wait_on_file(merged_dir + "merged_1" + extension_type)
        im = Image.open(merged_dir + "merged_1" + extension_type)

        # best jpeg quality since we won't be saving up disk space
        im.save(ffmpeg_pipe_subprocess.stdin, format=pipe_format, quality=95)
    
    # # #  # # #  # # #  # # #

    # # #  Progressive Frames Extractor (PFE) stuff  # # #

    if PFEOBJ == None:
        PFE_enabled = False

    else:
        PFE_enabled = True
        waifu2x_type = context.waifu2x_type
        if waifu2x_type == "vulkan":
            residual_image_ext_r = ""   # [WKR] ON WAIFU2X VULKAN .JPG.PNG
        else:
            residual_image_ext_r = ".jpg"

    # # #  # # #  # # #  # # #  # # #  # # #  # # #  # # #

    # Load the genesis image + the first upscaled image.
    frame_previous = Frame()
    frame_previous.load_from_string_wait(merged_dir + "merged_" + str(1) + extension_type)

    f1 = Frame()
    f1.load_from_string_wait(upscaled_dir + "output_" + get_lexicon_value(6, 1) + ".png")

    # When upscaling every frame between start_frame to frame_count, there's obviously no x + 1 at frame_count - 1 .
    # So just make a small note not to load that image. Pretty much load images concurrently until we get to x - 1
    last_frame = False

    for x in range(1, frame_count):

        #print("new index", x)
        
        ###################################
        # Loop-iteration pre-requirements #
        ###################################

        # Check if we're at the last image
        if x >= frame_count - 1:
            last_frame = True
            #print('Last frame')

        # load the next image ahead of time.
        if not last_frame:
            background_frame_load = AsyncFrameRead(upscaled_dir + "output_" + get_lexicon_value(6, x + 1) + ".png")
            background_frame_load.start()


        #######################
        # Loop-iteration Core #
        #######################

        logger.info("Upscaling frame " + str(x))


        prediction_data_file = pframe_data_dir + "pframe_" + str(x) + ".txt"
        residual_data_file = residual_data_dir + "residual_" + str(x) + ".txt"
        correction_data_file = correction_data_dir + "correction_" + str(x) + ".txt"
        fade_data_file = fade_data_dir + "fade_" + str(x) + ".txt"

        prediction_data_list = get_list_from_file(prediction_data_file)
        residual_data_list = get_list_from_file(residual_data_file)
        correction_data_list = get_list_from_file(correction_data_file)
        fade_data_list = get_list_from_file(fade_data_file)

        frame_next = make_merge_image(context, f1, frame_previous,
                                      prediction_data_list, residual_data_list,
                                      correction_data_list, fade_data_list)

        if PFE_enabled:
            """
            Two main things:

            Call next frame and remove the already used ones only
            if the minimal-disk setting is enabled on the config

            Delete the "already used" files (always index_to_remove behind)

            This way we clean the workspace as we're moving on with the encode
            """

            # write next frame to inputs
            PFEOBJ.next_frame()

            # get the files to delete "_r(emove)"

            index_to_remove = str(x - 2)

            prediction_data_file_r = pframe_data_dir + "pframe_" + index_to_remove + ".txt"
            residual_data_file_r = residual_data_dir + "residual_" + index_to_remove + ".txt"
            residual_image_r_1 = residual_images_dir + "output_" + get_lexicon_value(6, x) + residual_image_ext_r # delete the one we just used to not be w2x again
            residual_image_r_2 = residual_images_dir + "output_" + get_lexicon_value(6, x - 15) + residual_image_ext_r # fail safe if any gets not deleted
            correction_data_file_r = correction_data_dir + "correction_" + index_to_remove + ".txt"
            fade_data_file_r = fade_data_dir + "fade_" + index_to_remove + ".txt"
            merged_image_r = merged_dir + "merged_" + index_to_remove + extension_type

            input_image_r = input_frames_dir + "frame" + index_to_remove + ".jpg"
            upscaled_file_r = upscaled_dir + "output_" + get_lexicon_value(6, int(index_to_remove)) + ".png"

            compressed_file_static_r = compressed_static_dir + "compressed_" + index_to_remove + ".jpg"
            compressed_file_moving_r = compressed_moving_dir + "compressed_" + index_to_remove + ".jpg"

            residual_upscaled_r = upscaled_dir + "output_" + get_lexicon_value(6, int(index_to_remove)) + ".png"
            
            # mark them
            remove = [prediction_data_file_r, residual_data_file_r, residual_image_r_1, residual_image_r_2, correction_data_file_r,
                      fade_data_file_r, merged_image_r, input_image_r, upscaled_file_r, compressed_file_static_r,
                      compressed_file_moving_r, residual_upscaled_r]
            
            # remove
            for item in remove:
                if os.path.exists(item): #fail safe
                    os.remove(item)
                    #remove_file_wait(item)


        if not ffmpeg_pipe_encoding: # ffmpeg piping is disabled, traditional way
            
            # Write the image in the background for the preformance increase
            output_file_merged = workspace + "merged/merged_" + str(x + 1) + extension_type
            background_frame_write = AsyncFrameWrite(frame_next, output_file_merged)
            background_frame_write.start()
        
        else: #ffmpeg piping is enabled
            
            # Write the image directly into ffmpeg pipe
            im = frame_next.get_pil_image()
            im.save(ffmpeg_pipe_subprocess.stdin, format=pipe_format, quality=95)

        #######################################
        # Assign variables for next iteration #
        #######################################
        
        if not last_frame:
            
            #print("entering while loop")

            while not background_frame_load.load_complete:
                time.sleep(.5)
                #wait_on_file(upscaled_dir + "output_" + get_lexicon_value(6, x + 1) + ".png")

            f1 = background_frame_load.loaded_image

        frame_previous = frame_next

        # Ensure the file is loaded for background_frame_load. If we're on the last frame, simply ignore this section
        # Because the frame_count + 1 does not exist.






    if ffmpeg_pipe_encoding:
        print("Closing FFMPEG")
        ffmpeg_pipe_subprocess.stdin.close()
        ffmpeg_pipe_subprocess.wait()
        
        # add the original file audio to the nosound file
        migrate_tracks(context, nosound_file, input_file, output_file)


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

    global PFE_enabled

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
