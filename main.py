#!/usr/bin/env python3

import pytube
from pytube import YouTube
from argparse import ArgumentParser
import cv2
import numpy as np
import os
import shutil
import errno
import math
from glob import glob
from PIL import Image
import imagehash

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
        print('Downloading the video off youtube (video only, no audio)...')
        # search for a video stream to download, filtering for video only (no audio)
        stream = self.video.streams.filter(only_video=True, file_extension=self.extension, adaptive=True).first()
        # TODO: if filepath exists, don't download, instead throw an error recommending --skip-download
        filepath = f'{filename}.{self.extension}'
        # download the video
        # TODO: some kind of progress bar/output, this takes a while and prints nothing
        stream.download(filename=filepath)
        print(f'Done downloading, saved to "{filepath}"')
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
    # TODO: error when interval is negative or too big (aka bigger than the video)
    def extract_frames(self, interval_ms = 3000):
        print(f'Extracting screenshots from the video with interval {interval_ms / 1000} seconds...')
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
        print(f'\nScreenshots extracted and saved to directory "{self.filename}"')

    # crop an image vertically with cv2, overwriting existing image at filepath
    # image is an image object read with cv2
    # top and bottom pixel are the top and bottom pixel rows to crop down to
    # top of an image is 0 and the bottom (assuming 1920x1080) is 1080
    def crop_image(self, image_path, top_pixel, bottom_pixel):
        image = cv2.imread(image_path)
        cropped_image = image[top_pixel:bottom_pixel]
        cv2.imwrite(image_path, cropped_image)

    # attempts to automatically find the bounds to crop each image to sheet music only
    # does this by using cv2 to find the first row of pixels that's 100% white, then
    # find the last row of pixels that's 100% white
    # returns two values, the indices of those two rows respectively
    def guess_crop_bounds(self, image_path = None):
        if not image_path:
            image_path = glob(f'{self.filename}/*.jpg')[0]
        image = cv2.imread(image_path)
        top_bound = self.first_white_row(image)
        # if top_bound is None, just exit bc couldn't guess the bounds
        if not top_bound:
            return None, None
        # for bottom bound, do same as top except with image flipped vertically
        bottom_bound = len(image) - self.first_white_row(image[::-1])
        return top_bound, bottom_bound

    # returns index of first row in a cv2 image that's 100% white pixels
    # TODO: rework this to work when it's "close enough" to 100% white
    def first_white_row(self, image):
        white_row_idx = None
        # what a white pixel looks like to cv2
        white = np.array([255, 255, 255], dtype='uint8')
        for row_idx, row in enumerate(image):
            has_nonwhite = False
            # throw out first and last 10 pixels bc shading sometimes exists
            for pixel in row[10:-10]:
                # if the pixel is not white, skip the row
                if not np.array_equal(pixel, white):
                    has_nonwhite = True
                    break # break out of inner loop
            # now if has_nonwhite is True, row is NOT 100% white
            if has_nonwhite:
                continue # go to next row
            white_row_idx = row_idx
            break
        return white_row_idx

    # returns a sorted list of the .jpg filenames in the extracted frames directory
    def get_image_filenames(self):
        image_files = glob(f'{self.filename}/*.jpg')
        # sort filenames in the chronological order of the frames
        image_files.sort(key=lambda f: int(os.path.splitext(os.path.basename(f))[0]))
        return image_files

    # crop all extracted frames down to just the sheet music
    # given the top and bottom bounds to crop the images to
    def crop_frames(self, top, bottom):
        if top < 0 or bottom < 0 or bottom <= top:
            raise ValueError('Invalid input for cropping range')
        # list of all images to crop
        image_files = self.get_image_filenames()
        # if top or bottom are greater than the height of the images, limit them
        height = len(cv2.imread(image_files[0]))
        top = height - 1 if top >= height else top
        bottom = height if bottom > height else bottom
        print(f'Cropping screenshots to {top}px-{bottom}px...')
        for idx, image_file in enumerate(image_files):
            print(f'{round((idx+1) / len(image_files) * 10000) / 100}%', end='\r')
            self.crop_image(image_file, top, bottom)
        print()

    # removes the duplicate sheet music frames from the images directory
    # by comparing the images with the imagehash library, and deleting
    # the ones that are similar
    def remove_dupe_frames(self):
        print('Filtering cropped image files...')
        image_files = self.get_image_filenames()
        imagehashes = {}
        # calculate the perceptual hash of each image
        for filename in image_files:
            imagehashes[filename] = imagehash.phash(Image.open(filename))
        # filenames to remove (because they're duplicates)
        rm_filenames = []
        # if difference between two hashes is < threshold, they're similar, so remove one
        threshold = 5
        # leave out the last filename, because we're comparing each to the next
        for idx, filename in enumerate(image_files[:-1]):
            next_filename = image_files[idx+1]
            # if the images are similar
            if imagehashes[filename] - imagehashes[next_filename] < threshold:
                rm_filenames.append(next_filename)
        #print(f'Removing {", ".join([os.path.basename(f) for f in rm_filenames])}')
        for filename in rm_filenames:
            os.remove(filename)

    # clean up the working directory afterward: delete the video and the extracted images
    def cleanup(self, preserve_video = False, preserve_imgs = False):
        if not preserve_video:
            print(f'Cleanup: deleting file "{self.filepath}"')
            os.remove(self.filepath)
        if not preserve_imgs:
            print(f'Cleanup: deleting directory "{self.filename}"')
            shutil.rmtree(self.filename)


def main():
    parser = ArgumentParser(description='download a transcription video from youtube, screenshot all the sheet music over the course of the video and output it to a single file')
    parser.add_argument('link', type=str, help='youtube link to download the video from')
    parser.add_argument('--filename', type=str, metavar='filename', help='filename to save the downloaded video to (stem only), default is video title')
    # the type here is set to a lambda to split input by '-' and parse each into a int
    parser.add_argument('--crop', type=lambda s: [int(n) for n in s.split('-')[:2]], metavar='[px]-[px]', help='pixel range to vertically crop the screenshots to in order to only capture the sheet music, by default the program tries to process the images and guess the range')
    parser.add_argument('--interval', type=int, metavar='ms', default=3000, help='interval in ms between screenshots to grab from the video, default is 3000, larger interval is faster but might skip over some stuff')
    #parser.add_argument('--trim', type=str, metavar='X:XX-X:XX', help='specify start and end timestamps to trim the video to, useful to trim out intros/outros')
    #parser.add_argument('--output', type=str, metavar='filetype', choices=['pdf', 'jpg'], help='filetype to output the sheet music as, choose from either pdf or jpg')
    parser.add_argument('--skip-download', action='store_true', help='skip downloading the video and look for it in the current directory (implies --preserve-video)')
    parser.add_argument('--preserve-video', action='store_true', help='don\'t delete the downloaded video file afterward')
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
    grabber.extract_frames(args.interval)

    # crop images
    if args.crop:
        top_crop = args.crop[0]
        bottom_crop = args.crop[1]
    else:
        # attempt to guess the range to crop to in order to just get the sheet music
        top_crop, bottom_crop = grabber.guess_crop_bounds()
    if top_crop:
        grabber.crop_frames(top_crop, bottom_crop)
    
    # after cropping, remove all but one image of each row of sheet music
    grabber.remove_dupe_frames()

    # cleanup: delete video and images, unless otherwise specified in the options
    # assume --skip-download implies --preserve-video
    grabber.cleanup(args.preserve_video or args.skip_download, args.preserve_imgs)

if __name__ == '__main__':
    main()
