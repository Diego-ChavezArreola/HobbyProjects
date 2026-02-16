# ANKI BUDDY

ANKI BUDDY is a python script for sending and receiving notes via a shared google drive folder

## Installation

Use the install.sh file or run the following

```bash
pip3 install -e .
```

## Usage

```
options:
  -h, --help                Show this usage message and exit
  -s, --send                Uploads your last card to google drive and prints it's FILE_ID
  -g FILE_ID, --get FILE_ID Takes a FILE_ID and creates a Anki card from it
  -d, --download            Download the most recently added note from the shared drive
  -t TEST, --test TEST      Dev testing tool
```

## ToDo
```
Refactor
Follow some coding guidelines maybe
Make faster and smother using ankiconnect multi
Catch exceptions breakes easily too many bugs to list
```

