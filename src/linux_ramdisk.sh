# this scripts sets up an 256 MB tmpfs "ramdisk" in Linux
# for dandere2x usage. please, if you're going to
# use this, set the workspace on danere2x_linux.yaml
# to "../workspace/default/" (without quotes)
# and set ramdisk_mode to true. this will automatically
# enable ffmpeg_pipe_encoding and minimal_disk_usage

# the place the ramdisk dir will be is ../workspace/default/ramdisk
# so automatically d2x appends that /ramdisk to the processing
# pathes so everything image-data-wise will be stored there



# PLEASE RUN THIS AS SUDO LIKE THIS:

# sudo sh linux_ramdisk.sh



DIRECTORY=$(cd `dirname $0` && pwd)

cd $DIRECTORY

mkdir -p workspace/default/ramdisk

cd workspace/default

mount -t tmpfs -o size=256m tmpfs ./ramdisk/
