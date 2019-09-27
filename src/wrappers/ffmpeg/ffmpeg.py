from dandere2xlib.utils.dandere2x_utils import wait_on_file
from dandere2xlib.utils.json_utils import get_options_from_section
from context import Context
from PIL import Image

import multiprocessing
import subprocess
import threading
import logging
import time
import os


def trim_video(context: Context, output_file: str):
    """
    Create a trimmed video using -ss and -to commands from FFMPEG. The trimmed video will be named 'output_file'
    """

    input_file = context.input_file

    trim_video_command = [context.ffmpeg_dir,
                          "-hwaccel", context.hwaccel,
                          "-i", input_file]

    trim_video_time = get_options_from_section(context.config_file["ffmpeg"]["trim_video"]["time"])

    for element in trim_video_time:
        trim_video_command.append(element)

    trim_video_options = \
        get_options_from_section(context.config_file["ffmpeg"]["trim_video"]["output_options"], ffmpeg_command=True)

    for element in trim_video_options:
        trim_video_command.append(element)

    trim_video_command.append(output_file)

    console_output = open(context.log_dir + "ffmpeg_trim_video_command.txt", "w")
    console_output.write(str(trim_video_command))
    subprocess.call(trim_video_command, shell=False, stderr=console_output, stdout=console_output)


def extract_frames(context: Context, input_file: str):
    """
    Extract frames from a video using ffmpeg.
    """
    input_frames_dir = context.input_frames_dir
    extension_type = context.extension_type
    output_file = input_frames_dir + "frame%01d" + extension_type
    logger = logging.getLogger(__name__)
    frame_rate = context.frame_rate

    extract_frames_command = [context.ffmpeg_dir,
                              "-hwaccel", context.hwaccel,
                              "-i", input_file]

    extract_frames_options = \
        get_options_from_section(context.config_file["ffmpeg"]["video_to_frames"]['output_options'],
                                 ffmpeg_command=True)

    for element in extract_frames_options:
        extract_frames_command.append(element)

    extract_frames_command.append("-r")
    extract_frames_command.append(str(frame_rate))

    extract_frames_command.extend([output_file])

    logger.info("extracting frames")

    console_output = open(context.log_dir + "ffmpeg_extract_frames_console.txt", "w")
    console_output.write(str(extract_frames_command))
    subprocess.call(extract_frames_command, shell=False, stderr=console_output, stdout=console_output)

def concat_encoded_vids(context: Context, output_file: str):
    """
    Concatonate a video using 2) in this stackoverflow post.
    https://stackoverflow.com/questions/7333232/how-to-concatenate-two-mp4-files-using-ffmpeg

    The 'list.txt' should already exist, as it's produced in realtime_encoding.py
    """

    encoded_dir = context.encoded_dir

    text_file = encoded_dir + "list.txt"
    concat_videos_command = [context.ffmpeg_dir,
                             "-f", "concat",
                             "-safe", "0",
                             "-hwaccel", context.hwaccel,
                             "-i", text_file]

    concat_videos_option = \
        get_options_from_section(context.config_file["ffmpeg"]["concat_videos"]['output_options'], ffmpeg_command=True)

    for element in concat_videos_option:
        concat_videos_command.append(element)

    concat_videos_command.extend([output_file])

    console_output = open(context.log_dir + "ffmpeg_concat_videos_command.txt", "w")
    console_output.write((str(concat_videos_command)))
    subprocess.call(concat_videos_command, shell=False, stderr=console_output, stdout=console_output)


def migrate_tracks(context: Context, no_audio: str, file_dir: str, output_file: str):
    """
    Add the audio tracks from the original video to the output video.
    """
    migrate_tracks_command = [context.ffmpeg_dir,
                              "-i", no_audio,
                              "-i", file_dir,
                              "-map", "0:v:0?",
                              "-map", "1?",
                              "-c", "copy",
                              "-map", "-1:v?"]

    migrate_tracks_options = \
        get_options_from_section(context.config_file["ffmpeg"]["migrating_tracks"]['output_options'],
                                 ffmpeg_command=True)

    for element in migrate_tracks_options:
        migrate_tracks_command.append(element)

    migrate_tracks_command.extend([str(output_file)])

    console_output = open(context.log_dir + "migrate_tracks_command.txt", "w")
    console_output.write(str(migrate_tracks_command))
    
    # open a subprocess and wait to finish
    migrate_process = subprocess.Popen(migrate_tracks_command, shell=False, stderr=console_output, stdout=console_output)
    migrate_process.wait()

def create_video_from_specific_frames(context: Context, file_prefix, output_file, start_number, frames_per_video):
    """
    Create a video using the 'start_number' ffmpeg flag and the 'vframes' input flag to create a video
    using frames for a range of output images.
    """

    # load context
    logger = context.logger
    extension_type = context.extension_type
    input_files = file_prefix + "%d" + extension_type

    video_from_frames_command = [context.ffmpeg_dir,
                                 "-start_number", str(start_number),
                                 "-hwaccel", context.hwaccel,
                                 "-framerate", str(context.frame_rate),
                                 "-i", input_files,
                                 "-vframes", str(frames_per_video),
                                 "-r", str(context.frame_rate)]

    frame_to_video_option = get_options_from_section(context.config_file["ffmpeg"]["frames_to_video"]['output_options']
                                                     , ffmpeg_command=True)

    for element in frame_to_video_option:
        video_from_frames_command.append(element)

    video_from_frames_command.extend([output_file])

    logger.info("running ffmpeg command: " + str(video_from_frames_command))

    console_output = open(context.log_dir + "video_from_frames_command.txt", "w")
    console_output.write(str(video_from_frames_command))
    subprocess.call(video_from_frames_command, shell=False, stderr=console_output, stdout=console_output)


def apply_dandere2x_core_filters(context): 

    # applies core d2x filters to the input video

    #noisy_video = self.context.workspace + "noisy" + self.context.output_file_ext
    
    print("\n    PFE WORKAROUND: APPLY FILTERS BEFORE STARTED")

    start = time.time()

    subprocess.run([context.ffmpeg_dir, '-i', context.input_file,
                    '-loglevel', 'panic',
                    '-threads', str(min(multiprocessing.cpu_count()*1.5, 12)),
                    '-qscale:v:', '2',
                    '-vf', 'noise=c1s=8:c0f=u', context.noisy_video])
    
    print("  PFE WORKAROUND: TOOK:", round(time.time() - start, 2))

    return context.noisy_video



def count_frames(context):

    print("\n  PFE: Counting frames with ffmpeg, should be the fastest?...")

    start = time.time()

    process = subprocess.Popen([context.ffmpeg_dir, '-i', context.input_file,
                                '-map', '0:v:0', '-c', 'copy', '-vsync', '0', '-f', 'null', '-'], 
                                stdout=subprocess.PIPE, universal_newlines=True, stderr=subprocess.STDOUT)

    for line in process.stdout:
        if "frame" in line: # sample: frame=  239 fps=0.0 q=-1.0 Lsize=N/A time=00:00:09.87 bitrate=N/A speed=6.39e+03x
            line = line.replace("frame=", "")
            line = line.split("fps")[0].replace(" ", "")
            try:
                # if for some reason we get a line that has frames but it's not the last one
                total_frames = int(line)
                break
            except Exception:
                pass

    #print('\n\n\n\n')
    
    #print(stdout)
    #self.total_frames = stdout.split("frame= ")[1].split(" ")[0]

    print("\n    PFE: Finding frame count took: ", round(time.time() - start, 2), "sec")
    print("  PFE: Total number of frames:", total_frames)

    return total_frames



class Pipe():

    def __init__(self, context):    

        print("\n    WARNING: EXPERIMENTAL FFMPEG PIPING IS ENABLED\n")

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
        self.ffmpeg_pipe_images = self.context.ffmpeg_pipe_images
        self.realtime_encoding_enabled = self.context.realtime_encoding_enabled
        self.waifu2x_type = self.context.waifu2x_type

        # pipe stuff
        self.pipe_running = 1
        self.images_to_pipe = []
        
        self.nosound_file = self.context.nosound_file
        self.frame_rate = str(self.context.frame_rate)
        self.input_file = self.context.input_file
        self.output_file = self.context.output_file
        self.ffmpeg_dir = self.context.ffmpeg_dir
        self.ffmpeg_pipe_encoding_codec = self.context.ffmpeg_pipe_encoding_codec


        # ffmpeg muxer / demuxer options

        # video out
        if ".mkv" in self.nosound_file:
            self.flag_format = "matroska"

        elif ".mp4" in self.nosound_file:
            self.flag_format = "mp4"
        
        else: # defaults to mkv
            self.flag_format = "matroska"

        
        # pipe format and codec "read"
        # used to be an option between png and jpeg
        # but png too much slower (3x)
        self.input_vcodec = "mjpeg"
        self.pipe_format = "JPEG"



        self.ffmpeg_pipe_command = [self.ffmpeg_dir,
                                    '-threads', str(min(multiprocessing.cpu_count()*1.5, 12)),
                                    "-loglevel", "panic",
                                    '-y', '-f', 'image2pipe',
                                    #'-rtbufsize', '15M',
                                    #'-fflags', 'nobuffer',
                                    '-vcodec', self.input_vcodec, 
                                    '-r', self.frame_rate, 
                                    '-i', '-',
                                    '-threads', str(min(multiprocessing.cpu_count()*1.5, 12)),
                                    '-q:v', '2',
                                    #'-fflags', 'nobuffer',
                                    #'-vcodec', 'libx264', # 3, 4, 5 GBs of RAM roflmao
                                    # '-c:v', 'libvpx-vp9', # don't pass 1 GB, dead compression
                                    '-vcodec', self.ffmpeg_pipe_encoding_codec, # mpeg4 and libxvid only that "works"
                                    #'-rtbufsize', '15M',
                                    #'-bufsize', '15M',
                                    '-preset', 'normal',
                                    '-qscale:v', '6', # 1 (best) - 31 (worst)
                                    #'-crf', '17', #only for h264
                                    "-f", self.flag_format,
                                    '-vf', ' pp7=qp=4:mode=medium, deband=range=22:blur=false',
                                    '-r', self.frame_rate, 
                                    self.nosound_file]

        self.ffmpeg_pipe_subprocess = subprocess.Popen(self.ffmpeg_pipe_command, stdin=subprocess.PIPE)

        # pipe the first merged image as it will not be done afterwards
        wait_on_file(self.merged_dir + "merged_1" + self.extension_type)
        im = Image.open(self.merged_dir + "merged_1" + self.extension_type)

        # best jpeg quality since we won't be saving up disk space
        im.save(self.ffmpeg_pipe_subprocess.stdin, format=self.pipe_format, quality=95)

        threading.Thread(target=self.write_to_pipe).start()


    def save(self, frame, _): # '_' to ignore the "x" var needed in AsyncWrite on merge.py

        # Write the image directly into ffmpeg pipe
        # by adding image to image_to_pipe list
        # kinda similar to AsyncFrameWrite

        while True:
            if len(self.images_to_pipe) < 10: # buffer limit
                self.images_to_pipe.append(frame)
                break
            time.sleep(0.05)


    def write_to_pipe(self):
        while self.pipe_running:
            if len(self.images_to_pipe) > 0:
                img = self.images_to_pipe.pop(0).get_pil_image() # get the first image and remove it from list
                img.save(self.ffmpeg_pipe_subprocess.stdin, format=self.pipe_format, quality=100)
            time.sleep(0.05)

        # close and finish audio file

        print("\n  Closing FFMPEG as encode finished...")
        
        self.ffmpeg_pipe_subprocess.stdin.close()
        self.ffmpeg_pipe_subprocess.wait()
        
        print("  Migrating audio tracks from the original video..")

        # add the original file audio to the nosound file
        migrate_tracks(self.context, self.nosound_file,
                       self.input_file, self.output_file)

        print("  Finished migrating tracks.")


    def wait_finish_stop_pipe(self):
        
        print("\n    Waiting for the ffmpeg-pipe-encode buffer list to end....")
        
        while self.images_to_pipe:
            time.sleep(0.05)

        self.pipe_running = 0