#!/usr/bin/env python3

import pytube
from pytube import YouTube
from argparse import ArgumentParser
import os

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
            print(f'Found "{video.title}" on youtube')
        except pytube.exceptions.RegexMatchError:
            print('ERROR: not a valid youtube link')
        except pytube.exceptions.VideoUnavailable:
            print('ERROR: video unavailable')
        else:
            valid = True
            self.video = video
        return valid

    # download the video at self.link, saving it to filename
    # by default, filename is set to the video's title
    # skip parameter is for skipping the pytube download and looking for the video in current directory
    def download(self, filename = None, skip = False):
        self.filename = filename if filename else self.video.title
        if skip:
            if not os.path.exists(self.filename + '.mp4'):
                # TODO: error handling is all over the place, gotta fix that
                raise ValueError
            print(f'Found {self.filename}.mp4')
        else:
            print('downloading the video...')
            # download the video into current directory, filtering for video only (no audio)
            self.video.streams.filter(only_video=True, file_extension='mp4', adaptive=True).first().download(filename=self.filename + '.mp4')
            print(f'Done downloading, saved to {self.filename}.mp4')


def main():
    parser = ArgumentParser(description='download a transcription video from youtube, screenshot all the sheet music over the course of the video and output it to a single pdf')
    parser.add_argument('link', type=str, help='youtube link to download the video from')
    parser.add_argument('--filename', type=str, metavar='filename', help='filename to save the downloaded video to (stem only), default is video title')
    parser.add_argument('--skip-download', action='store_true', help='skip downloading the video and look for it in the current directory')
    args = parser.parse_args()

    grabber = SheetGrabber(args.link)
    if not grabber.verify_link():
        return
    grabber.download(args.filename, args.skip_download)

if __name__ == '__main__':
    main()
