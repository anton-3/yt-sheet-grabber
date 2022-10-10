#!/usr/bin/env python3

import pytube
from pytube import YouTube
from argparse import ArgumentParser
import cv2
import os
import shutil
import errno
import math

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
        # self.filepath is just self.filename but includes the file extension

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

    # extract frames from the downloaded video and save them as images
    # interval: the time in ms between each frame to save, default 3 seconds
    def extract_frames(self, interval_ms = 3000):
        print('Extracting frames from the video file...')
        # get VideoCapture object for downloaded video
        capture = cv2.VideoCapture(self.filepath)
        # get the video's total frame count and frames per second
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = round(capture.get(cv2.CAP_PROP_FPS))
        # make a directory to store the images, same name as video without extension
        if not os.path.isdir(self.filename):
            os.mkdir(self.filename)

        interval_seconds = interval_ms / 1000
        # number of frames in a second times interval in seconds is interval in frames
        interval_frames = round(fps * interval_seconds) # must be an integer
        # total number of images that'll be saved
        total_images = math.ceil(frame_count / interval_frames)
        # running count for number of images saved
        image_count = 0

        # step through frames in increments of interval_frames
        for frame in range(0, frame_count, interval_frames):
            # set cv2 to point to this frame to decode
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
            success, image = capture.read()
            # if success is False, there was no frame to read for some reason
            if not success:
                print('Ran out of frames to read, which shouldn\'t have happened')
                break

            image_filepath = f'{self.filename}/{frame}.jpg'
            # write the image to image_filepath
            cv2.imwrite(image_filepath, image)
            image_count += 1
            print(f'{round(image_count / total_images * 10000) / 100}%', end='\r')
        print('\nFrames extracted')

    # clean up the working directory afterward: delete the video and the extracted images
    def cleanup(self, preserve_video = False, preserve_imgs = False):
        if not preserve_video:
            print(f'Cleanup: deleting file {self.filepath}')
            os.remove(self.filepath)
        if not preserve_imgs:
            print(f'Cleanup: deleting directory {self.filename}')
            shutil.rmtree(self.filename)


def main():
    parser = ArgumentParser(description='download a transcription video from youtube, screenshot all the sheet music over the course of the video and output it to a single file')
    parser.add_argument('link', type=str, help='youtube link to download the video from')
    parser.add_argument('--filename', type=str, metavar='filename', help='filename to save the downloaded video to (stem only), default is video title')
    parser.add_argument('--skip-download', action='store_true', help='skip downloading the video and look for it in the current directory')
    parser.add_argument('--preserve-video', action='store_true', help='don\'t delete the downloaded video file (audio only) afterward')
    parser.add_argument('--preserve-imgs', action='store_true', help='don\'t delete the extracted image files afterward')
    args = parser.parse_args()

    # create SheetGrabber object, verify the video link is valid
    grabber = SheetGrabber(args.link)
    if not grabber.valid_link:
        return

    # download the video, save it to a file
    # or just verify the video file exists if --skip-download is specified
    filename = args.filename if args.filename else grabber.find_filename()
    if args.skip_download:
        grabber.skip_download(filename)
    else:
        grabber.download(filename)

    # extract frames from the video, save them to image files
    grabber.extract_frames()

    # clean up: delete video and images
    grabber.cleanup(args.preserve_video, args.preserve_imgs)

if __name__ == '__main__':
    main()
