# Dandere2x - Fast Waifu2x Video Upscaling 

## Tremeschin's optimization on Python part of dandere2x

I'll be testing this Linux only but might work fine on Windows OS everything I do, trying to keep it OS and distro agnostic as much as possible.

I'm focusing on optimizations rather than new features since I don't fully understand dandere2x yet.

For history purposes, the first huge commit was two days of work and with a 10 second 480p anime as a sample, the original code for dandere2x finished on avg (3 runs) in 93.9 seconds and my optimizations finished on avg (3 runs) 86.0 seconds. 7.5% speed increase overhaul it ain't much but it's honest work.

Well, considing I chanced not the most compute heavy part of the code.. I think this is going pretty well.

The two tests were done using waifu2x-ncnn-vulkan installed from the AUR on a Arch Linux computer with a RX 570 GPU. I stopped in 3 runs because the time was consistent betwen them: 93.7s, 96.3s, 91.9s; 84.0s, 83.8s, 83.8s.

Performance gains from now might be slower and slower since we're hitting the limiting factor of waifu2x upscale time, but who knows what can we do to circumvent this?

I mean, the cpp part of the code at least on my tests were ahead of the waifu2x upscaling process, we could save some time on having all the merged files ready to upscale finished before the last major call of waifu2x doing a kinda "wait" process to save a few seconds but that's not gonna be much on longer videos at all.

## Todo:

- Clean the code and the comments
- Make it more procedural (not everybody gonna have the binaries in /usr/bin/)
- Possible optimizations on string concatenation? "Hello " + name vs "Hello {name}"
- List comprehension instead of loops?
- Better usage of block size and waifu2x tile size? Might require a few R&D
- Debug ocasional gpu infinite loading/unloading waifu2x and doing nothing
- Profile more the code, couldn't to it properly


Now here's the original README from dandere2x utill the time I forked it:

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
