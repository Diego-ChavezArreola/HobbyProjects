import argparse
import os
import ctypes
import sys
import re

ANIME_PATH = 'D:\ビデオ\アニメ'
IGNORE_FILES = ['.parts', '映画', 'desktop.ini', 'ICO']


def tryint(s):
    try:
        return int(s)
    except:
        return s


def alphanum_key(s):
    """ Turn a string into a list of string and number chunks.
        "z23a" -> ["z", 23, "a"]
    """
    return [tryint(c) for c in re.split('([0-9]+)', s)]


def sort_nicely(l):
    """ Sort the given list in the way that humans expect.
    """
    l.sort(key=alphanum_key)


def arg_parsing():
    parser = argparse.ArgumentParser(
        description='Share Anki cards through google drive.')
    parser.add_argument(
        '-a',
        '--anime',
        help='Takes name of anime in your database',
        action='store')
    parser.add_argument(
        '-i',
        '--ignore',
        help='Ignore certain files',
        action='store')
    args = parser.parse_args()
    if args.anime == None:
        args.anime = input('Name of the anime you would like renamed:')
    elif args.ignore == None:
        args.ignore = input('Files you would like to ignore')
    return args.anime, args.ignore


def get_anime_dir():
    anime_list = os.listdir(ANIME_PATH)
    [anime_list.remove(anime) for ig in IGNORE_FILES for anime in reversed(
        anime_list) if ig in anime]
    return anime_list


def rename_subs(input_anime, anime_list, ignore_anime):
    found_anime = [
        anime for anime in anime_list if input_anime.lower() in anime.lower()]
    if len(found_anime) > 1:
        print('Found more than one anime with that name please choose which one you mean.')
        for i, extra in enumerate(found_anime):
            print(f'[{i}] {extra}')
        num = int(input())
        found_anime = [found_anime[num]]

    path = ANIME_PATH + '\\' + found_anime[0]

    sub_format = str(
        input("Extension of subtitle files(ex: .sub, .srt, etc): "))

    tempVidList = [name for name in os.listdir(path) if name.endswith(
        '.mp4') or name.endswith('.mkv') or name.endswith('.avi')]
    if ignore_anime:
        vidFiles = [video for video in tempVidList if ignore_anime not in video]
    else:
        vidFiles = tempVidList
    subFiles = [name for name in os.listdir(path) if name.endswith(sub_format)]

    sort_nicely(vidFiles)
    sort_nicely(subFiles)

    os.chdir(path)

    try:
        assert(len(subFiles) == len(vidFiles))
        for i, vname in enumerate(vidFiles):
            print("{0} renamed to {1} ".format(
                subFiles[i], os.path.splitext(vname)[0]))
            os.rename(subFiles[i], os.path.splitext(vname)[0]+sub_format)
    except AssertionError:
        print(len(subFiles))
        print(len(vidFiles))
    print('Done renaming!')
    return


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def main():
    if is_admin():
        input_anime, ignore_anime = arg_parsing()
        rename_subs(input_anime, get_anime_dir(), ignore_anime)
    else:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1)


if __name__ == "__main__":
    main()
