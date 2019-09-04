# Dandere2x - Fast Waifu2x Video Upscaling

Dandere upscales a video using a project based on a Neural Network called Waifu2x with many techniques to speed up this process like block matching, frame compression and multiprocessing.

First of all, you shouldn't be running dandere2x if by any chance you don't have a somewhat decent GPU or a really good CPU for longer videos. It'll litteraly take forever in a slow/medium CPU only system or on a slow GPU one. For short videos you can try using it and it'll probably work just fine, just keep an eye on the RAM usage, FFMPEG likes to eat it a bit when multithreaded in mass like dandere2x does.

## Tremeschin's optimization branch

I'll be testing this Linux only but might work fine on Windows OS everything I do, trying to keep it OS and distro agnostic as much as possible.

I'm focusing on optimizations rather than new features since I don't fully understand dandere2x yet.

For history purposes, the first huge commit was two days of work and with a 10 second 480p anime as a sample, the original code for dandere2x finished on avg (3 runs) in 93.9 seconds and my optimizations finished on avg (3 runs) 86.0 seconds. 7.5% speed increase overhaul it ain't much but it's honest work.

Well, considing I changed not the most compute heavy part of the code.. I think this is going pretty well.

The two tests were done using `waifu2x-ncnn-vulkan` installed from the AUR on a Arch Linux computer with a RX 570 GPU. I stopped in 3 runs because the time was consistent betwen them: 93.7s, 96.3s, 91.9s; 84.0s, 83.8s, 83.8s.

Well, considering an average of 5.4~ seconds per frame on upscaling the bare frame with waifu2x, it would take 240\*5.4 seconds to finish it!! Just about 21.6 minutes for a 10 second 24 frames per second video and we're finishing* it in under two minutes!!

Performance gains from now might be slower and slower since we're hitting the limiting factor of waifu2x upscale time, but who knows what can we do to circumvent this?

*yeah, it's a lossy process being applied here but on higher resolutions it's not even noticeable

## Usage

Well, since I already include the compiled cpp code in the externals folder the process gonna be much easier. Keep in mind I only support _officially_ dandere2x using the Linux `waifu2x-ncnn-vulkan` and `waifu2x-converter-cpp` binaries. It might work on Windows just fine as I said but I just can't easily test it.

I really recommend you use a Arch based system here like Manjaro because even aka_katto had some troubles setting up the `waifu2x-ncnn-vulkan` on a Ubuntu based machine, well, if you know how to do it properly you're free!! AFAIK the code on every distro should work just fine.

Ok, let's get into the usage of dandere2x itself and after then setting up the dependencies on Linux

First you gotta clone this **branch**, not the master one like so:

> git clone --single-branch --branch tremx-optimizations https://github.com/Tremeschin/dandere2x

Then cd into the src directory:

> cd dandere2x/src

Now you have two choices: the GUI way or the terminal way.

## GUI Way

After _cding_ to the src directory just run a simple

> python gui_driver.py

Select the file you want to upscale, select the desired output file name and press that upscale button!

Please, try using the **vulkan waifu2x** process by selecting it in the top left corner.

Please, read the section Installing dependencies.

## Terminal way

First you gotta configure the `dandere2x_linux.json` file
The most important parts are in the sections:

> dandere2x/usersettings/input_file  
> dandere2x/usersettings/output_file  
> dandere2x/usersettings/block_size  
> waifu2x_ncnn_vulkan/* _everything_  

They are pretty self explanatory except the `waifu2x_ncnn_vulkan` part, let's take it slowly.

### waifu2x_ncnn_vulkan

I **strongly** recommend using the vulkan version, it's quite faster than other and "more compatible" on modern gpus.

The **path** and the **file** name of `waifu2x_ncnn_vulkan` in that section refers to the installed binary on your system

You can try leaving it off and letting the program finding and asking what waifu2x binary you want to use in the first run or configuring it yourself. 

I recommend just running the program and see if it works, it auto detects if the file pointed in the json is actually a file.

### output_options

You basically want to mess with the `-t` argument here, it's the tile size waifu2x will be upscaling the images. It really depends on your GPU, the higher you put, the more memory it'll use and faster\* it will be. The lower, less memory, slower. I find 256 pretty decent in speed/memory/temperature ratio for my GPU.


*there's a point you almost see no gains in a big tile size. 


## Running in the terminal

Just as simple as:

> python scratch_paper.py

Of course, with everything configured properly.

Please, read next section.

## Installing dependencies:

I'll only be posting the commands with a Arch Linux based system here. Keep in mind it works perfectly on other distros, you just gotta search and configure yourself a working waifu2x client.

If you haven't got a AUR helper installed like yay (that I recommend using it), install it with the following command:

> sudo pacman -S git && git clone https://aur.archlinux.org/yay.git && cd yay && makepkg -si

If you haven't uncommentted the `[multilib]` section in your `/etc/pacman.conf`, edit that file with your preffered text editor. For simplicity use nano:

> sudo nano /etc/pacman.conf

And uncomment the lines:

> \[multilib]  
> Include = /etc/pacman.d/mirrorlist

Now you have acess to the AUR

Running the following command should get everything working in the waifu2x side:

> yay -Syu ncnn-git waifu2x-ncnn-vulkan-git

Won't be teaching you setting up a python environment with PIP, it's easy to search but installing the dependencies is really important

I'm not a big fan of virtual envs like aka_katto recommended on it's first Linux release so in the same `./dandere2x/src` directory run a

> pip install -r requirements.txt --user

And you should be good to go

**Keep in mind everything here can be done with any distro and potentially in Windows as well, you gotta figure out yourself on other distros installing a working waifu2x client and the necessary python environment and dependencies.**

## Todo:

- Clean the code and the comments
- Make it more procedural (not everybody gonna have the binaries in /usr/bin/)
- Possible optimizations on string concatenation? "Hello " + name vs "Hello {name}"
- List comprehension instead of loops?
- Better usage of block size and waifu2x tile size? Might require a few R&D
- Debug ocasional gpu infinite loading/unloading waifu2x and doing nothing
- Profile more the code, couldn't to it properly



# Original README from dandere2x

## What is Dandere2x

Dandere2x reduces the time needed for Waifu2x to upscale animation (sometimes live-action) videos by applying compression techniques. Just as Netflix uses compression to quickly stream videos to your home, Dandere2x uses compression to expedite the waifu2x upscaling process.


## Links 

Documentation:

https://dandere2x.readthedocs.io/

Subreddit:

https://www.reddit.com/r/Dandere2x/

Telegram Server:

https://t.me/joinchat/KTRznBIPPNCbHkUqnwT8pA

Patreon:

https://www.patreon.com/dandere2x

## Current Features

- Interpolated Video Compression
- Minimum Quality Loss (MQL) dictated by DCT quantization. 
- Weighted Blocks (Fade to Black, Fade to White) 
- Real-time Video Encoding
- Interactive GUI


## How does Dandere2x work?

Dandere2x is a compression algorithm specifically designed to help compress anime so Waifu2x can work faster. In short, Dandere2x looks for redundancies in Anime to reduce the time needed to upscale a video. A longer, more in-depth post can be found here. 

https://github.com/aka-katto/dandere2x/wiki/How-Dandere2x-Works

## GUI Preview

![Image of the GUI](https://i.imgur.com/PWe7NzV.png)

## Development Status

Dandere2x is in development and research, primarily by a single individual (the author). Currently, Dandere2x is in beta-candidate testing, which the author hopes to release as a beta release.

Updates, thoughts, and progress can be found in the form of posts on the Dandere2x subreddit:

https://www.reddit.com/r/Dandere2x/


## Can I help with Dandere2x?

Dandere2x has been very reliant on the community for its development. Testing newest and nightly releases and reporting bugs and crashes has allowed Dandere2x to become usable over many months. 

Furthermore, the read the docs are underdocumented, and some of the code can be messy. Contributing your thoughts and ideas to either would go a long way - feel free to comment your ideas on what can or should be improved on. 

## FAQ

Q: What is the difference between Dandere2x and Video2x?

A: Video2x aims for quality over speed. If you're looking for the best-possible looking video, Video2x is more streamlined and provides lossless upscaling. Dandere2x, on the other hand, is still in development, is much faster than video2x, but at the cost of being lossy. 


Q: How does Dandere2x work?

A: https://github.com/aka-katto/dandere2x/wiki/How-Dandere2x-Works

## Related Resources

[Video2x](https://github.com/k4yt3x/video2x): A lossless video enlarger/video upscaler achieved with waifu2x.

## Credits

This project relies on the following software and projects.

- waifu2x-caffe
- waifu2x
- FFmpeg
- STB Image
- waifu2x-vulkan
- waifu2x-ncnn-vulkan
- waifu2x-converter-cpp-deadsix 

Code was used from the following projects

- Video2x
