#!/usr/bin/env python3

from argparse import ArgumentParser
from yt_sheet_grabber import CommandLine

def main():
    commandline = CommandLine()
    commandline.run_parser()

if __name__ == '__main__':
    main()
