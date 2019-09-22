import subprocess
import time
import cv2

"""
success,image = vidcap.read()
count = 0
while success:
  cv2.imwrite("frame%d.jpg" % count, image)     # save frame as JPEG file      
  success,image = vidcap.read()
  print('Read a new frame: ', success)
  count += 1
"""

class ProgressiveFramesExtractor():
    def __init__(self, context):
        self.count = 1
        self.context = context

        self.cap = cv2.VideoCapture(self.context.input_file)
        
        #self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        

    # TODO: since the python-opencv CAP_PROP_FRAME_COUNT is a estimation,
    # we can't rely on counting the dir len() when in minimal_disk mode,
    # so hope reading these frames without saving them but writing afterwards
    # gives a performance increase?
    def count_frames(self):

        start = time.time()

        cap = cv2.VideoCapture(self.context.input_file)
        frames = 1

        while True:
            success, image = self.cap.read()
            if success:
                frames += 1
            else:
                break
        
        self.total_frames = frames

        print("    Finding frame count took: ", round(time.time() - start, 2), "sec")
        print("  Total number of frames:", self.total_frames)

    def count_frames_ffmpeg(self):
        process = subprocess.Popen([self.context.ffmpeg_dir, '-i', self.context.input_file, '-map', '0:v:0', '-c', 'copy', '-f', 'null', '-'], stdout=subprocess.PIPE)
        process.wait()
        stdout = process.stdout
        print('\n\n\n\n')
        
        print(stdout)
        #self.total_frames = stdout.split("frame= ")[1].split(" ")[0]

        self.total_frames = 0


    def first_frame(self):
        success, image = self.cap.read()
        
        if success:
            cv2.imwrite(self.context.input_frames_dir + "frame%d.jpg" % self.count, image)
            self.count += 1


    def next_frame(self):
        success, image = self.cap.read()
        
        if success:
            cv2.imwrite(self.context.input_frames_dir + "frame%d.jpg" % self.count, image)
            self.count += 1

        else:
            return 1


class ctx():
    def __init__(self):
        self.input_frames_dir = "test/"
        self.input_file = "5sec.mkv"
        self.ffmpeg_dir = "ffmpeg"
"""
test = ProgressiveFramesExtractor(ctx())

test.total_frames
"""
#test.first_frame()


#for _ in range(400):
#    test.next_frame()