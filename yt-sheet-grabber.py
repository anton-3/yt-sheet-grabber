#!/usr/bin/env python3

# TODO:
# error handling
# argparser
# progress bar on pytube download (and general progress output)
# converting the video to images with opencv
# cropping the frame images to just the sheet music
# putting all the images together into a pdf/master image
# lots of command line arguments for everything
# release binary?

from pytube import YouTube
import sys

# link of video to download is currently passed as a command line argument
link = sys.argv[1]

yt = YouTube(link)
# download the video into current directory, filtering for video only
print(f'Downloading {yt.title}...')
yt.streams.filter(only_video=True, file_extension='mp4', adaptive=True).first().download()
print('Done downloading')
# pytube gives the downloaded video this filename by default
filename = f'{yt.title}.mp4'

