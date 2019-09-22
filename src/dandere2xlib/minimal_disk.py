from PIL import Image
import subprocess
import time
import cv2

class ProgressiveFramesExtractor():
    """
    This class has some wrapping stuff with python-opencv
    its main functionality is extracting frame by frame of the video
    since doing this with only ffmpeg (it's possible) AFAIK will yield
    much worse performance.

    It'll be running based on the context variable with dandere2x
    
    """
    def __init__(self, context):
        self.count = 1
        self.context = context
        self.cap = None
        
        #self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))


    def load(self):
        self.cap = cv2.VideoCapture(self.context.input_file)


    # TODO: since the python-opencv CAP_PROP_FRAME_COUNT is a estimation,
    # we can't rely on counting the dir len() when in minimal_disk mode,
    # so hope reading these frames without saving them but writing afterwards
    # gives a performance increase?
    def count_frames(self):

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


    def count_frames_ffmpeg(self): # doesnt work
        
        process = subprocess.Popen([self.context.ffmpeg_dir, '-i', self.context.input_file, '-map', '0:v:0', '-c', 'copy', '-f', 'null', '-'], stdout=subprocess.PIPE)
        process.wait()
        stdout = process.stdout
        print('\n\n\n\n')
        
        print(stdout)
        #self.total_frames = stdout.split("frame= ")[1].split(" ")[0]

        self.total_frames = 0


    def next_frame(self):

        success, image = self.cap.read()
        
        if success:
            cv2.imwrite(self.context.input_frames_dir + "frame%s.jpg" % self.count, image, [cv2.IMWRITE_JPEG_QUALITY, 100])
            self.count += 1

        
    def next_frame_ffmpeg(): # barely work

        frame_out = self.context.input_frames_dir + "frame%s.jpg" % self.count

        process = subprocess.Popen([self.context.ffmpeg_dir, '-loglevel', 'panic', '-i', self.context.input_file,  '-vf', 'select=eq(n\,%s)' % self.count, '-vframes', '1', '-q:v', '1', '-qscale:v:', '2', frame_out])#, stdout=subprocess.PIPE)
        process.wait()

        self.count += 1
        


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