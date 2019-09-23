from dandere2xlib.utils.dandere2x_utils import wait_on_file
from wrappers.frame.frame import Frame
from context import Context

import time
import os


def compress_frames(context: Context):
    """
    Use frame's save_image_quality function to save a series of compressed images, which are used in
    Dandere2x_Cpp as a loss function. This function on it's own is a bit esoteric - I recommend reading
    the white paper to understand why we need to compress these frames.

    Input:
        - context

    Output:
        - All the images in 'input_frames' compressed into two different folders, each with their own
          level of compression.
    """

    inputs_dir = context.input_frames_dir
    frame_count = context.frame_count
    quality_moving_ratio = context.quality_moving_ratio
    compressed_static_dir = context.compressed_static_dir
    compressed_moving_dir = context.compressed_moving_dir
    quality_minimum = context.quality_minimum
    extension_type = context.extension_type

    # start from 1 because ffmpeg's extracted frames starts from 1
    for x in range(1, frame_count):

        ordinal_frame = "compressed_" + str(x) + ".jpg"

        # if the compressed frame already exists, don't compress it
        if os.path.exists(compressed_static_dir + ordinal_frame):
            continue
        

        # _wait for PFE since we'll not get all inputs first hand
        # TODO this sometimes gets IndexError

        while True: # was giving lots of errors with inputs nominal, insist loading then
            try:
                frame = Frame()
                frame.load_from_string_wait(inputs_dir + "frame" + str(x) + extension_type)
                break

            except IndexError:
                #print("insisted loading", x) # debugging purposes
                time.sleep(0.5)

        frame.save_image_quality(compressed_static_dir + ordinal_frame, quality_minimum)
        frame.save_image_quality(compressed_moving_dir + ordinal_frame, int(quality_minimum * quality_moving_ratio))
