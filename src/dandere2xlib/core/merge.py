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
from dandere2xlib.utils.dandere2x_utils import get_lexicon_value, get_list_from_file, wait_on_file, remove_file_wait, delete_used_files
from wrappers.ffmpeg.ffmpeg import migrate_tracks, Pipe
from wrappers.frame.asyncframe import AsyncFrameWrite, AsyncFrameRead
from wrappers.frame.frame import Frame




class AsyncWrite():
    def __init__(self, context):
        self.context = context
        self.merged_dir = self.context.merged_dir
        self.extension_type = self.context.extension_type

    def save(self, img, x):
        # Write the image in the background for the preformance increase
        output_file_merged = self.merged_dir + "merged_" + str(x + 1) + self.extension_type
        background_frame_write = AsyncFrameWrite(img, output_file_merged)
        background_frame_write.start()




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

    # use pipe or not depending on context
    # NOTE: both of these classes have the
    # same named save() method
    if context.ffmpeg_pipe_images:
        corelogic = Pipe(context)
    else:
        corelogic = AsyncWrite(context)


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

        # Loop-iteration pre-requirements

        # Check if we're at the last image
        if x >= frame_count - 1:
            last_frame = True

        # load the next image ahead of time.
        if not last_frame:
            background_frame_load = AsyncFrameRead((context.residual_upscaled_dir + "output_" + 
                                                    get_lexicon_value(6, x + 1) + ".png"))
            background_frame_load.start()


        # Loop-iteration Core

        logger.info("Merging frame " + str(x))

        frame_next = make_merge_image(context, f1, frame_previous, x)

        if PFE_enabled:
            delete_used_files(context, x)
            PFEOBJ.next_frame()

        corelogic.save(frame_next, x)


        # Assign variables for next iteration        

        if not last_frame:
            while not background_frame_load.load_complete:
                time.sleep(0.5)
                # wait_on_file(upscaled_dir + "output_" + get_lexicon_value(6, x + 1) + ".png")
                # causes trouble with minimal-disk because the auto-deletion stuff

            f1 = background_frame_load.loaded_image

        frame_previous = frame_next

        # Ensure the file is loaded for background_frame_load. If we're on the last frame, simply ignore this section
        # Because the frame_count + 1 does not exist.


    if context.ffmpeg_pipe_images:
        corelogic.wait_finish_stop_pipe()



def make_merge_image(context: Context, frame_residual: Frame, frame_previous: Frame, ind):
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

    list_predictive = get_list_from_file(context.pframe_data_dir + "pframe_" + str(ind) + ".txt")
    list_residual = get_list_from_file(context.residual_data_dir + "residual_" + str(ind) + ".txt")
    list_corrections = get_list_from_file(context.correction_data_dir + "correction_" + str(ind) + ".txt")
    list_fade = get_list_from_file(context.fade_data_dir + "fade_" + str(ind) + ".txt")

    # Load context
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
