import argparse
from pickle import TRUE
import tempfile
import shutil
import ankibuddy
import os
import itertools
import threading
import time
import sys
from .ankibuddy import Sender, Receiver
from .GoogleAuth import Create_Service
from .config import read_config

PATH = os.path.abspath(os.path.join(ankibuddy.__file__, '..', '..',))
CLIENT_SECRET_FILE = os.path.abspath(os.path.join(ankibuddy.__file__, '..', '..', 'credentials.json'))
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']

DONE = False
ACTION_TYPE = 'loading'

def starting_actions(action):
    global ACTION_TYPE
    ACTION_TYPE = action
    t = threading.Thread(target=animate)
    t.start()

def main():
    parser = argparse.ArgumentParser(
        description='Share Anki cards through google drive.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-s',
        '--send',
        help='Uploads your last card to google drive',
        action='store_true')
    group.add_argument(
        '-g',
        '--get',
        # nargs='*',
        help='Takes fileID(s) of notes and creates them into anki cards')
    group.add_argument(
        '-d',
        '--download',
        # nargs='?',
        # const=1,
        help='Download the most recently added note(s) from the shared drive',
        action='store_true')
    group.add_argument(
        '-t',
        '--test',
        help='dev testing tool',
        action='store_true')
    group.add_argument(
        '-r',
        '--reauth',
        help='Force google reauth flow if refresh token has expired',
        action='store_true')
    group.add_argument(
        '-c',
        '--config',
        help='Create config file is one doesnt exist and print the path',
        action='store_true')
    args = parser.parse_args()
    
    try:
        global DONE
        temp_dir = tempfile.mkdtemp()
        service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, PATH, args.reauth, SCOPES)
        if args.send:
            starting_actions('sending')
            s = Sender(service, temp_dir)
            DONE = TRUE
            sys.stdout.write(f'\rNote uploaded to drive! ID: {s.file_id}')

        elif args.get:
            starting_actions('getting')
            r = Receiver(service, temp_dir, args.get)
            DONE = TRUE
            sys.stdout.write(f'\rGot note for {r.note.focus_word} successfully!')
            
        elif args.download:
            starting_actions('downloading')
            rd = Receiver(service, temp_dir)
            DONE = TRUE
            sys.stdout.write(f'\rMost recently added note for {rd.note.focus_word} downloaded and added!')
        
        elif args.config:
            read_config(print_path=args.config)
            
        elif args.test:
            DONE = TRUE
            print('You have not set up a test')
        
        else:
            DONE = TRUE
            print('use anki_buddy -h to see usage')    
            
    finally:
        DONE = TRUE
        shutil.rmtree(temp_dir)
        
def animate():
    for c in itertools.cycle(['|', '/', '-', '\\']):
        if DONE:
            break
        sys.stdout.write(f'\r{ACTION_TYPE} ' + c)
        sys.stdout.flush()
        time.sleep(0.1)

if __name__ == '__main__':
    main()