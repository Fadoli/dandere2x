from fractions import Fraction

from wrappers.ff_wrappers.ffprobe import get_video_info, get_width_height, get_frame_rate


# A simple way to just have a class w/ the contents we need to operate dandere2x

class VideoSettings:

    def __init__(self, ffprobe_dir, video_file: str):
        self.ffprobe_dir = ffprobe_dir
        self.settings_json = get_video_info(self.ffprobe_dir, video_file)

        print(self.settings_json)

        try:
            self.height = self.settings_json['streams'][0]['height']
            self.width = self.settings_json['streams'][0]['width']
            self.frame_rate = float(Fraction(self.settings_json['streams'][0]['r_frame_rate']))

        except KeyError:
            self.height, self.width = get_width_height(self.ffprobe_dir, video_file)
            self.frame_rate = float(Fraction(get_frame_rate(self.ffprobe_dir, video_file)))