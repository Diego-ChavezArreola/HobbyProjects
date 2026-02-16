import os
import argparse

from .prompts import ankibuddy_menu
from .ankibuddy import download_note, send_note
from .config import change_config
from .banner import print_banner


def main():
    parser = argparse.ArgumentParser(description="Share Anki cards through noSQL DB.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-s",
        "--send",
        help="Uploads your most recently create note to database",
        action="store_true",
    )
    group.add_argument(
        "-d",
        "--download",
        help="Download the most recently added note from the database",
        action="store_true",
    )
    group.add_argument(
        "-c",
        "--config",
        help="Edit or create config file",
        action="store_true",
    )
    args = parser.parse_args()

    if args.send:
        send_note()
    elif args.download:
        download_note()
    elif args.config:
        change_config()
    else:
        answer_dict = {
            "send most recent": send_note,
            "download most recent": download_note,
            "change settings": change_config,
            "exit": exit,
        }
        while True:
            os.system("cls")
            print_banner()
            result = ankibuddy_menu()
            answer_dict[result]()


if __name__ == "__main__":
    main()
