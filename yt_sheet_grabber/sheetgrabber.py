import pytube
from pytube import YouTube
import cv2
import numpy as np
import os
import shutil
import errno
import math
from glob import glob
from PIL import Image
import imagehash
import fitz
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

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

    # trims the downloaded video down to between the timestamps start and end
    # timestamps are strings "XX:XX" or "X:XX", e.g. "0:15", "13:37"
    def trim_video(self, start, end):
        for timestamp in [start, end]:
            if timestamp.count(':') != 1 or not ''.join(timestamp.split(':')).isdigit():
                raise ValueError('Invalid timestamp given')
        start_sec = int(start.split(':')[0]) * 60 + int(start.split(':')[1])
        end_sec = int(end.split(':')[0]) * 60 + int(end.split(':')[1])
        video_filename = f'{self.filename}.{self.extension}'
        old_filename = f'{self.filename}-OLD.{self.extension}'
        print(f'Trimming {video_filename} to {start_sec}s-{end_sec}s...')
        # ffmpeg can't edit files in-place, so have to rename the original and delete it after
        os.rename(video_filename, old_filename)
        ffmpeg_extract_subclip(old_filename, start_sec, end_sec, targetname=video_filename)
        os.remove(old_filename)

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
                print('\nRan out of frames to read, which might happen when the video is trimmed', end='')
                break

            image_filepath = os.path.join(self.filename, f'{frame}.jpg')
            # write the image to image_filepath
            cv2.imwrite(image_filepath, image)
            image_count += 1
            print(f'{round(image_count / total_images * 10000) / 100}%', end='\r')
        print(f'\nScreenshots extracted and saved to directory "{self.filename}"')

    # crop an image vertically with cv2, overwriting existing image at filepath
    # image is an image object read with cv2
    # top and bottom pixel are the top and bottom pixel rows to crop down to
    # top of an image is 0 and the bottom (assuming 1920x1080) is 1080
    def _crop_image(self, image_path, top_pixel, bottom_pixel):
        image = cv2.imread(image_path)
        cropped_image = image[top_pixel:bottom_pixel]
        cv2.imwrite(image_path, cropped_image)

    # TODO: this implementation with cv2 is slow, inefficient, and inconsistent
    # attempts to automatically find the bounds to crop each image to sheet music only
    # does this by using cv2 to find the first row of pixels that's 100% white, then
    # find the last row of pixels that's 100% white
    # returns two values, the indices of those two rows respectively
    def guess_crop_bounds(self, image_path = None):
        if not image_path:
            image_path = self._get_image_filenames()[0]
        image = cv2.imread(image_path)
        top_bound = self._first_white_row(image)
        # if top_bound is None, just exit bc couldn't guess the bounds
        if not top_bound:
            return None, None
        # for bottom bound, do same as top except with image flipped vertically
        bottom_bound = len(image) - self._first_white_row(image[::-1])
        return top_bound, bottom_bound

    # returns index of first row in a cv2 image that's 100% white pixels
    # TODO: rework this to work when it's "close enough" to 100% white
    def _first_white_row(self, image):
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
    def _get_image_filenames(self):
        image_files = glob(os.path.join(self.filename, '*.jpg'))
        # sort filenames in the chronological order of the frames
        image_files.sort(key=lambda f: int(os.path.splitext(os.path.basename(f))[0]))
        return image_files

    # crop all extracted frames down to just the sheet music
    # given the top and bottom bounds to crop the images to
    def crop_frames(self, top, bottom):
        if top < 0 or bottom < 0 or bottom <= top:
            raise ValueError('Invalid input for cropping range')
        # list of all images to crop
        image_files = self._get_image_filenames()
        # if top or bottom are greater than the height of the images, limit them
        height = len(cv2.imread(image_files[0]))
        top = height - 1 if top >= height else top
        bottom = height if bottom > height else bottom
        print(f'Cropping screenshots to {top}px-{bottom}px...')
        for idx, image_file in enumerate(image_files):
            print(f'{round((idx+1) / len(image_files) * 10000) / 100}%', end='\r')
            self._crop_image(image_file, top, bottom)
        print()

    # removes the duplicate sheet music frames from the images directory
    # by comparing the images with the imagehash library, and deleting
    # the ones that are similar
    def remove_dupe_frames(self):
        print('Filtering cropped image files...')
        image_files = self._get_image_filenames()
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

    # stitch all the sheet music images together vertically into one (very long) image
    def output_result_image(self):
        image_files = self._get_image_filenames()
        images = [Image.open(filename) for filename in image_files]
        result_width, _ = images[0].size
        # sum of all the heights of each individual image
        result_height = sum([img.size[1] for img in images])
        result = Image.new('RGB', (result_width, result_height))
        for idx, image in enumerate(images):
            # the height to place the image at in the result
            # sum of the heights of the previous images
            start_height = sum([img.size[1] for img in images[:idx]])
            result.paste(im=image, box=(0, start_height))
        result_filename = f'{self.filename}.jpg'
        print(f'Saving output image to {result_filename}...')
        result.save(result_filename)

    # takes a list of PIL images and returns a shorter list of them stitched together vertically
    # stitches them together until they're close to but less than the dimensions of A4 paper
    def _images_to_pages(self, images):
        page_ratio = 842 / 595 # ratio of height to width of A4 paper (roughly sqrt of 2)
        width = images[0].width # width is same for every image
        # height to make each page in pixels, equal to width times the A4 ratio
        page_height = int(page_ratio * width)
        page_images = []
        current_page = Image.new('RGB', (width, page_height), color='white')
        current_page_height = 0
        for image in images:
            if current_page_height + image.height > page_height:
                # if there isn't enough space to add image to this page,
                # then append current page to page_images
                page_images.append(current_page)
                # and reset the variables to create the next page
                current_page = Image.new('RGB', (width, page_height), color='white')
                current_page_height = 0
            current_page.paste(im=image, box=(0, current_page_height))
            current_page_height += image.height
        # add the last page, if it wasn't already added
        if current_page not in page_images:
            page_images.append(current_page)
        return page_images

    # takes a filename of a pdf and resize its pages to the normal size for A4 paper
    # since by default with a 1920x1080 video, pdf is 1920 pixels wide which is massive
    def _convert_pdf_to_a4(self, filename):
        input_pdf = fitz.open(filename)
        result_pdf = fitz.open()
        for page in input_pdf:
            dimensions = fitz.paper_rect('a4')
            new_page = result_pdf.new_page(width=dimensions.width, height=dimensions.height)
            new_page.show_pdf_page(new_page.rect, input_pdf, page.number)
        input_pdf.close()
        result_pdf.save(filename)
        result_pdf.close()

    # stitch all the sheet music images together vertically into a pdf
    def output_result_pdf(self):
        image_files = self._get_image_filenames()
        images = [Image.open(filename) for filename in image_files]
        page_images = self._images_to_pages(images)
        result_filename = f'{self.filename}.pdf'
        print(f'Saving output pdf to {result_filename}...')
        page_images[0].save(result_filename, 'PDF', resolution=100, save_all=True, append_images=page_images[1:])
        self._convert_pdf_to_a4(result_filename)

    # clean up the working directory afterward: delete the video and the extracted images
    def cleanup(self, preserve_video = False, preserve_imgs = False):
        if not preserve_video:
            print(f'Cleanup: deleting file "{self.filepath}"')
            os.remove(self.filepath)
        if not preserve_imgs:
            print(f'Cleanup: deleting directory "{self.filename}"')
            shutil.rmtree(self.filename)
