import os
import sys
import time

from context import Context


# todo
# This could probably be improved visually for the user.. it's not the most pleasing to look at
# Also, in a very niche case the GUI didn't catch up with the deletion of files, so it ceased updating

def print_status(context: Context):
    workspace = context.workspace
    extension_type = context.extension_type
    frame_count = context.frame_count

    last_10 = [0]

    for x in range(1, frame_count):
        #for showing 100%
        percent = int((x / (frame_count - 1)) * 100)

        average = 0
        for time_count in last_10:
            average = average + time_count

        average = round(average / len(last_10), 2)

        sys.stdout.write('\r')
        sys.stdout.write("Frame: [%s] %i%%    Average of Last 10 Frames: %s sec / frame" % (x, percent, average))

        file_dir = workspace + "merged/merged_" + str(x + 1) + extension_type
        if len(last_10) == 10:
            last_10.pop(0)

        now = time.time()

        exists = os.path.isfile(file_dir)
        while not exists:
            exists = os.path.isfile(file_dir)
            time.sleep(.01)

        later = time.time()
        difference = float(later - now)
        last_10.append(difference)
    
    #after upscaling done
    print("\nMerging all upscaled content...")
