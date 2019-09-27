from PIL import Image
import multiprocessing
import subprocess
import threading
import time
import cv2
import sys
import os

class ProgressiveFramesExtractor():
    """
    This class has some wrapping stuff with python-opencv
    its main functionality is extracting frame by frame of the video
    since doing this with only ffmpeg (it's possible) AFAIK will yield
    much worse performance.

    It'll be running based on the context variable with dandere2x

    """
    def __init__(self, context, countfunc="ffmpeg", extractfunc="ffmpeg"):

        self.countfunc = countfunc if countfunc in ["cv2", "ffmpeg", "ffprobe"] else exit(-1)
        self.extractfunc = extractfunc if extractfunc in ["cv2", "ffmpeg"] else exit(-1)

        self.count = 1
        self.context = context
        self.cap = None
        self.get_frames_offset = 0 # ffmpeg extracts 240 frames with -i video frame%d.jpg but reads 239 frames on video file, same with cv2 and ffprobe (239)

        self.threads_count = multiprocessing.cpu_count()*1.5 # for better FFmpeg performance
        
        #self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) # not accurate since this is a aproximation


    # problem: exponentially slower?
    # or does ffmpeg gets right on the frame we want
    # here we can apply filters with easy though
    def next_frame_ffmpeg(self, frameindex, wait=False): # barely work
        #if not self.count > self.total_frames + 1:
        frame_out = self.context.input_frames_dir + "frame%s.jpg" % (frameindex)

        command = [self.context.ffmpeg_dir, '-loglevel', 'panic', '-i', self.context.input_file,
                   '-threads', str(self.threads_count), '-vsync', '0',
                   '-vf', 'select=eq(n\,%s), noise=c1s=8:c0f=a' % (frameindex - 1),
                   '-vframes', '1', '-q:v', '1', '-qscale:v', '2', 
                   frame_out]

        process = subprocess.Popen(command)
        
        if wait:
            process.wait()

        else:
            # can hang OS if used to much because RAM
            pass
            

