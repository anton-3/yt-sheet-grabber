#!/usr/bin/env python3

# TODO:
# error handling
# argparser
# progress bar on pytube download (and general progress output)
# converting the video to images with opencv
# https://www.thepythoncode.com/article/extract-frames-from-videos-in-python
# cropping the frame images to just the sheet music
# putting all the images together into a pdf/master image
# lots of command line arguments for everything
# release binary?
# make a separate branch for gui version with pysimplegui eventually?

# example vids
# https://www.youtube.com/watch?v=x-3XxK6N0kM
# https://www.youtube.com/watch?v=6jGeX0vQvSQ

import pytube
from pytube import YouTube
from argparse import ArgumentParser
import sys

class SheetGrabber:
    def __init__(self, link):
        self.link = link

    # check if self.link is valid and downloadable
    # (mostly by catching errors from pytube)
    # example valid: https://www.youtube.com/watch?v=x-3XxK6N0kM
    # example invalid: asdf
    # example invalid: https://www.youtube.com/watch?v=aioghaidjaghsdofj
    def verify_link(self):
        valid = False
        try:
            # get the video by the link
            # pytube throws a RegexMatchError if this isn't a valid youtube link
            video = YouTube(self.link)
            # pytube throws a VideoUnavailable error on yt.title call if it can't find the video
            print(f'Found "{video.title}"')
        except pytube.exceptions.RegexMatchError:
            print('Error: not a valid youtube link')
        except pytube.exceptions.VideoUnavailable:
            print('Error: video unavailable')
        else:
            valid = True
        return valid

    def download(self):
        # download the video into current directory, filtering for video only (no audio)
        video.streams.filter(only_video=True, file_extension='mp4', adaptive=True).first().download()
        print('Done downloading')
        # pytube gives the downloaded video this filename by default
        filename = f'{video.title}.mp4'

def main():
    # link of video to download is currently passed as a command line argument
    link = sys.argv[1]
    #parser = ArgumentParser(description='download a transcription video from youtube, screenshot all the sheet music over the course of the video and output it to a single pdf')
    grabber = SheetGrabber(link)
    if not grabber.verify_link():
        return
    print('downloading the video...')
    # do download stuff here

if __name__ == '__main__':
    main()
