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



DIRECTORY=$(cd `dirname $0` && pwd) &&

cd $DIRECTORY &&

rm -r ./workspace/default/processing/* ; # remove its contents if any

mkdir -p ./workspace/default/processing && # create it fail-safe

cd workspace/default &&

mount -t tmpfs -o size=256m tmpfs ./processing/

echo "[Tremx]: Ignore no such file or directory if any, sudo rm -rf is dangerous"

# to unmount the ramdisk either reboot the system
# or get a terminal in the workspace/default/
# and sudo umount ./ramdisk