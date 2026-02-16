import re
import requests
from tqdm import tqdm


def main():
    for i in range(610, 731):
        response = requests.get(
            f'https://podcast.sokoani.com/SA/mp3/s{i}.mp3', stream=True)
        file_size = int(response.headers.get('content-length', 0))
        block_size = 1024
        progress_bar = tqdm(total=file_size, unit='iB', unit_scale=True)
        with open(f'そこ☆あに\\s{i}.mp3', 'wb') as f:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                f.write(data)
        progress_bar.close()
        if file_size != 0 and progress_bar.n != file_size:
            print("ERROR, something went wrong")
        else:
            print(f'Done downloading s{i}.mp3')


if __name__ == '__main__':
    main()
