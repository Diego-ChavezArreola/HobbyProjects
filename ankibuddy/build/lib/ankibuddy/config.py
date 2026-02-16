import os
from appdirs import user_config_dir
from configparser import ConfigParser

FOCUS_WORD = 'VocabKanji'
SENT = 'SentKanji'
TRANSLATION = 'SentEng'
DEFINITION = 'VocabDef'
IMAGE = 'Image'
SENT_AUDIO = 'SentAudio'
WORD_AUDIO = 'VocabAudio'
MODEL_NAME = 'Basic'
DECK_NAME = 'Default'
FIELDS = [
    FOCUS_WORD,
    SENT,
    TRANSLATION,
    DEFINITION,
    IMAGE,
    SENT_AUDIO,
    WORD_AUDIO,
    MODEL_NAME]

def read_config(print_path=False):
    config_path = user_config_dir('ankibuddy', appauthor='baker')
    first_path = os.path.abspath(os.path.join(config_path, '..'))
    if not os.path.isdir(first_path): os.mkdir(first_path)
    if not os.path.isdir(config_path): os.mkdir(config_path)
    if print_path: print(config_path)
    config = ConfigParser()
    config.read(f'{config_path}\\config.ini')
    try:
        fields = [config['Anki Fields'][field] for field in list(config['Anki Fields'])]
        folder = [config['Google Drive']['SHARED_FOLDER']][0]
        return fields, folder
    except KeyError as key:
        print('Config file either does not exist or is not setup correctly. Using default config')
        return FIELDS
    