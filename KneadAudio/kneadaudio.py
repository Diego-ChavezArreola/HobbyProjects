import json
import argparse
import shutil
from ankiconnect import invoke
SENTENCE_DATABASE = 'D:\\オーディオ\\文\\audio_files'
JSON_PATH = SENTENCE_DATABASE + '\\sentences\\all_v10.json'
DESKTOP_PATH = "C:\\Users\\8BitPC\\Desktop"


def search(query):
    with open(JSON_PATH, 'r') as f:
        sent_data = json.load(f)
        f.close()
    for sent in sent_data:
        if sent['jap'] == query:
            return sent['audio_jap']


def main():
    parser = argparse.ArgumentParser(
        description='Get sent audio fast from local db.')
    parser.add_argument(
        '-i',
        '--input',
        help='Sentence you want the audio from',
        action='store'
    )
    args = parser.parse_args()
    results = search(args.input)
    path = SENTENCE_DATABASE + '\\' + results
    shutil.copy2(path, DESKTOP_PATH)
    print(f'Done copying {results}!')


if __name__ == '__main__':
    main()
