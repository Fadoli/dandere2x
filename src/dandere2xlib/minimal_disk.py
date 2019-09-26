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

    def ffmpeg_filters_workaround(self): 

        # applies core d2x filters to the input video, FORCES using cv2 to extract the frames
        # and sets the output noisy video as the input for future

        
        self.extractfunc = "cv2"
        original_video = self.context.input_file

        noisy_video = self.context.workspace + "noisy" + self.context.output_file_ext
        
        print("\n    PFE WORKAROUND: APPLY FILTERS BEFORE STARTED")

        start = time.time()

        subprocess.run([self.context.ffmpeg_dir, '-i', original_video,
                       '-loglevel', 'panic',
                       '-threads', str(self.threads_count),
                       '-qscale:v:', '2',
                       '-vf', 'noise=c1s=8:c0f=u', noisy_video])
        
        print("  PFE WORKAROUND: TOOK:", round(time.time() - start, 2))

        self.context.input_file = noisy_video

        self.load()

        return self.context.input_file


    def load(self):
        self.cap = cv2.VideoCapture(self.context.input_file)
    
    # For easier changes in the code
    # set the function to use here 

    def count_frames(self):
        if self.countfunc == "ffmpeg":
            return self.count_frames_ffmpeg()

        elif self.countfunc == "ffprobe":
            return self.count_frames_ffprobe()

        else:
            return self.count_frames_cv2


    def next_frame(self):
        if self.extractfunc == "ffmpeg":
            threading.Thread(target=self.next_frame_ffmpeg, args=(self.count,), daemon=True).start()
            self.count += 1
            #self.next_frame_ffmpeg()

        elif self.extractfunc == "cv2":
            self.next_frame_cv2()
            self.count += 1
            #self.next_frame_cv2()


    # # #  # # #  # # #  # # #


    def count_frames_cv2(self):
        
        print("\n  PFE Counting frames old way, will take a while...")

        start = time.time()

        counter = cv2.VideoCapture(self.context.input_file)
        frames = 0

        while True:
            success, image = counter.read()
            if success:
                frames += 1
            else:
                break
        
        self.total_frames = frames

        print("\n    PFE: Finding frame count took: ", round(time.time() - start, 2), "sec")
        print("  PFE: Total number of frames:", self.total_frames)

        return self.total_frames


    def count_frames_ffmpeg(self):

        print("\n  PFE: Counting frames with ffmpeg, should be the fastest?...")

        start = time.time()

        process = subprocess.Popen([self.context.ffmpeg_dir, '-i', self.context.input_file,
                                    '-map', '0:v:0', '-c', 'copy', '-vsync', '0', '-f', 'null', '-'], 
                                    stdout=subprocess.PIPE, universal_newlines=True, stderr=subprocess.STDOUT)

        for line in process.stdout:
            if "frame" in line: # frame=  239 fps=0.0 q=-1.0 Lsize=N/A time=00:00:09.87 bitrate=N/A speed=6.39e+03x
                line = line.replace("frame=", "")
                line = line.split("fps")[0].replace(" ", "")
                try:
                    # if for some reason we get a line that has frames but it's not the last one
                    self.total_frames = int(line) + self.get_frames_offset
                    break
                except Exception:
                    pass

        #print('\n\n\n\n')
        
        #print(stdout)
        #self.total_frames = stdout.split("frame= ")[1].split(" ")[0]

        print("\n    PFE: Finding frame count took: ", round(time.time() - start, 2), "sec")
        print("  PFE: Total number of frames:", self.total_frames)

        return self.total_frames


    def count_frames_ffprobe(self): # this is by far the preffered way

        print("\n  PFE: Counting frames with ffprobe, should be fast?...")

        start = time.time()

        stdout = subprocess.run([self.context.ffprobe_dir, '-v', 'error', '-count_frames',
                                 '-threads', str(self.threads_count), '-vsync', '0',
                                 '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames',
                                 self.context.input_file], check=True, stdout=subprocess.PIPE).stdout

        stdout = stdout.decode("utf-8")

        stdout = stdout.split("\n")
        stdout = stdout[1] # we'll get something like ['[STREAM]', 'nb_read_frames=239', '[/STREAM]', '']
        stdout = stdout.split("=")[1] # get the number (string)

        self.total_frames = int(stdout) + self.get_frames_offset

        print("\n    PFE: Finding frame count took: ", round(time.time() - start, 2), "sec")
        print("  PFE: Total number of frames:", self.total_frames)

        return self.total_frames




    def next_frame_cv2(self): # TODO need to apply core d2x filters # FIXED: FFMPEG WORKAROUND
        success, image = self.cap.read()
        
        if success:
            cv2.imwrite(self.context.input_frames_dir + "frame%s.jpg" % self.count, image, [cv2.IMWRITE_JPEG_QUALITY, 100])


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
            


"""

class ctx():
    def __init__(self):
        self.input_frames_dir = "cv2png/"
        self.input_file = "5sec.mkv"
        self.ffmpeg_dir = "ffmpeg"

test = ProgressiveFramesExtractor(ctx())
test.load()

for _ in range(3000):
    test.next_frame()
"""


#test.first_frame()


#for _ in range(400):
#    test.next_frame()