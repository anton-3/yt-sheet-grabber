#!/usr/bin/env python3

import pytube
from pytube import YouTube
from argparse import ArgumentParser
import os
import errno

class SheetGrabber:
    # link: the link to the youtube video to grab sheet music from
    # extension: the file extension to download and save the video as
    def __init__(self, link, extension = 'mp4'):
        self.link = link
        self.extension = extension

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
            print(f'Found video "{self.video.title}"')

    # download the video at self.link, saving it to filename
    def download(self, filename):
        print('Downloading the video off youtube... (might take a sec)')
        # search for a video stream to download, filtering for video only (no audio)
        stream = self.video.streams.filter(only_video=True, file_extension=self.extension, adaptive=True).first()
        # TODO: if filepath exists, don't download, instead throw an error recommending --skip-download
        filepath = f'{filename}.{self.extension}'
        # download the video
        # TODO: some kind of progress bar/output, this takes a while and prints nothing
        stream.download(filename=filepath)
        print(f'Done downloading, saved to {filepath}')
        self.filename = filename
        self.filepath = filepath

    # skip downloading the video, just use a video file instead
    # this mainly exists to set self.filename and verify the video file exists
    def skip_download(self, filename):
        filepath = f'{filename}.{self.extension}'
        print(f'Skipping video download, looking for {filepath}...')
        if not os.path.isfile(filepath):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), filepath)
        print(f'Found {filepath}')
        self.filename = filename
        self.filepath = filepath

    # finds the default OS-compatible filename provided by pytube for the downloaded video
    # useful for when the user doesn't specify filename and you need to find one to use
    # returns just the stem of the filename, doesn't include file extension
    def find_filename(self):
        # this returns a default filename including the file extension
        filepath = self.video.streams.first().default_filename
        # strip the extension, then return
        filename = os.path.splitext(filepath)[0]
        return filename


def main():
    parser = ArgumentParser(description='download a transcription video from youtube, screenshot all the sheet music over the course of the video and output it to a single pdf')
    parser.add_argument('link', type=str, help='youtube link to download the video from')
    parser.add_argument('--filename', type=str, metavar='filename', help='filename to save the downloaded video to (stem only), default is video title')
    parser.add_argument('--skip-download', action='store_true', help='skip downloading the video and look for it in the current directory')
    args = parser.parse_args()

    grabber = SheetGrabber(args.link)
    if not grabber.valid_link:
        return

    filename = args.filename if args.filename else grabber.find_filename()
    if args.skip_download:
        grabber.skip_download(filename)
    else:
        grabber.download(filename)

if __name__ == '__main__':
    main()
