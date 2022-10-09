#!/usr/bin/env python3

import pytube
from pytube import YouTube
from argparse import ArgumentParser

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
    def download(self, filename = None):
        # default filename is the video title
        self.filename = filename if filename else self.video.title
        # download the video into current directory, filtering for video only (no audio)
        self.video.streams.filter(only_video=True, file_extension='mp4', adaptive=True).first().download(filename=self.filename + '.mp4')
        print(f'Done downloading, saved to {self.filename}.mp4')


def main():
    parser = ArgumentParser(description='download a transcription video from youtube, screenshot all the sheet music over the course of the video and output it to a single pdf')
    parser.add_argument('link', type=str)
    args = parser.parse_args()

    grabber = SheetGrabber(args.link)
    if not grabber.verify_link():
        return
    print('downloading the video...')
    grabber.download()

if __name__ == '__main__':
    main()
