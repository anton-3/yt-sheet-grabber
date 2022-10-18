from argparse import ArgumentParser
from .sheetgrabber import SheetGrabber

class CommandLine:
    def __init__(self):
        self.parser = self.create_parser()

    def create_parser(self):
        parser = ArgumentParser(description='download a transcription video from youtube, screenshot all the sheet music over the course of the video and output it to a single file')
        parser.add_argument('link', type=str, help='youtube link to download the video from')
        parser.add_argument('--filename', type=str, metavar='filename', help='filename to save the downloaded video to (stem only), default is video title')
        # the type here is set to a lambda to split input by '-' and parse each into a int
        parser.add_argument('--crop', type=lambda s: [int(n) for n in s.split('-')[:2]], metavar='[px]-[px]', help='pixel range to vertically crop the screenshots to in order to only capture the sheet music, by default the program tries to process the images and guess the range')
        parser.add_argument('--interval', type=int, metavar='ms', default=3000, help='interval in ms between screenshots to grab from the video, default is 3000, larger interval is faster but might skip over some stuff')
        parser.add_argument('--trim', type=lambda s: [t for t in s.split('-')[:2]], metavar='X:XX-X:XX', help='specify start and end timestamps to trim the video to, useful to trim out intros/outros')
        parser.add_argument('--output', type=str, metavar='filetype', default='pdf', choices=['pdf', 'jpg', 'both'], help='filetype to output the sheet music as, choose from either pdf (default), jpg, or both')
        parser.add_argument('--skip-download', action='store_true', help='skip downloading the video and look for it in the current directory (implies --preserve-video)')
        parser.add_argument('--preserve-video', action='store_true', help='don\'t delete the downloaded video file afterward')
        parser.add_argument('--preserve-imgs', action='store_true', help='don\'t delete the extracted image files afterward')
        return parser

    def run_parser(self, arguments = None):
        args = self.parser.parse_args(arguments) # if passed None, uses sys.argv
        self.args = args

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

        # trim the video before working on it if --trim is specified
        if args.trim:
            grabber.trim_video(args.trim[0], args.trim[1])

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

        # export all the remaining sheet music images into a pdf (and/or jpg, specified by --output)
        if args.output in ['pdf', 'both']:
            grabber.output_result_pdf()
        if args.output in ['jpg', 'both']:
            grabber.output_result_image()

        # cleanup: delete video and images, unless otherwise specified in the options
        # assume --skip-download implies --preserve-video
        grabber.cleanup(args.preserve_video or args.skip_download, args.preserve_imgs)
