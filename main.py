#!/usr/bin/env python3

import pytube
from pytube import YouTube
from argparse import ArgumentParser
import os

class SheetGrabber:
    def __init__(self, link):
        self.link = link

        # this is a dumb way to check if the link is valid but I couldn't think of a better one
        # initially set that the link is invalid, if it gets through try/except, set it to True
        self.valid_link = False
        try:
            # get the video by the link
            # pytube throws a RegexMatchError if this isn't a valid youtube link
            self.video = YouTube(self.link)
            # this throws one of several errors if the video is unavailable
            # https://pytube.io/en/latest/_modules/pytube/__main__.html#YouTube.check_availability
            self.video.check_availability()
        except pytube.exceptions.RegexMatchError:
            print('ERROR: not a valid youtube link')
        except Exception as e:
            print(f'ERROR: video unavailable')
            # print(f'ERROR: video unavailable, error was {e.__class__.__name__}')
        else:
            self.valid_link = True
            print(f'Found "{self.video.title}"')

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
    if not grabber.valid_link:
        return
    grabber.download(args.filename, args.skip_download)

if __name__ == '__main__':
    main()
