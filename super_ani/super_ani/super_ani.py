import requests
import qbittorrentapi
import os
import zipfile
import rarfile
import re
import shutil
import argparse

from PIL import Image
from thefuzz import fuzz
from bs4 import BeautifulSoup
from colorama import Fore, Style, init

init(autoreset=True)

def search_anilist(anime_name):
    query = '''
    query ($search: String) {
      Media (search: $search, type: ANIME) {
        id
        status
        title {
          romaji
          native
        }
        coverImage {
          extraLarge
        }
      }
    }
    '''
    
    variables = {
        'search': anime_name
    }
    
    url = 'https://graphql.anilist.co'
    
    response = requests.post(url, json={'query': query, 'variables': variables})
    data = response.json()
    
    if data and 'data' in data and 'Media' in data['data']:
        anime_data = data['data']['Media']
        return {
            'id': anime_data['id'],
            'status': anime_data['status'],
            'title_romaji': anime_data['title']['romaji'],
            'title_native': anime_data['title']['native'],
            'cover_image': anime_data['coverImage']['extraLarge']
        }
    else:
        return None

def search_nyaa(query, category=None, sub_category=None):
    base_url = 'https://nyaaapi.onrender.com/nyaa'
    params = {
        'q': query,
        'category': category,
        'sub_category': sub_category,
        'sort': 'seeders'
    }
    params = {k: v for k, v in params.items() if v is not None}
    response = requests.get(base_url, params=params, headers={'accept': 'application/json'})
    if response.status_code == 200:
        results = response.json()
        return results
    else:
        print(f"Failed to fetch data: HTTP {response.status_code}")
        return None
    
def display_and_select_torrents(torrents):
    terminal_width = os.get_terminal_size().columns
    reserved_space = 40  

    print(Fore.YELLOW + f"{'Index'.ljust(6)}{'Title'.ljust(terminal_width - reserved_space + 4)}{Fore.MAGENTA}Size  {Fore.GREEN}Seeds  {Fore.RED}Leechers")
    for i, torrent in enumerate(torrents, start=1):
        title = torrent['title']
        size = torrent['size']
        seeds = torrent['seeders']
        leechers = torrent['leechers']

        title_space = terminal_width - reserved_space

        if len(title) > title_space:
            title = title[:title_space-3] + "..."

        print(f"{Fore.CYAN}{str(i).ljust(6)}{Fore.BLUE}{title.ljust(title_space)}{Fore.MAGENTA}{size.rjust(8)}  {Fore.GREEN}{str(seeds).rjust(5)}  {Fore.RED}{str(leechers).rjust(8)}")

    selected_indices = input(Fore.GREEN + "Enter the number(s) of the torrents you want to download (e.g., 1, 3, 5): ")
    selected_indices = selected_indices.split(',')

    selected_torrents = []
    for index in selected_indices:
        try:
            idx = int(index.strip()) - 1  
            if 0 <= idx < len(torrents):
                selected_torrents.append(torrents[idx])
            else:
                print(Fore.RED + f"No torrent found for selection {index}.")
        except ValueError:
            print(Fore.RED + f"Invalid selection: {index}. Please enter numbers only.")

    return selected_torrents

def download_torrent(magnet_link, anime_name_native, save_path):
    qbt_client = qbittorrentapi.Client(host='localhost', port=8080, username='admin', password='adminadmin')

    try:
        qbt_client.auth_log_in()
    except qbittorrentapi.LoginFailed as e:
        print(f"Failed to log in to qBittorrent: {e}")
        return None

    qbt_client.torrents_add(urls=magnet_link, save_path=save_path, category="アニメ", rename=anime_name_native)
    print(f"Added torrent to qBittorrent: {magnet_link}")

def display_subtitles_in_table(subtitles):
    terminal_width = os.get_terminal_size().columns
    reserved_space = 40  

    title_space = terminal_width - reserved_space

    compressed_subtitles = [s for s in subtitles if any(ext in s[0].lower() for ext in ['.zip', '.rar'])]
    other_subtitles = [s for s in subtitles if s not in compressed_subtitles]
    sorted_subtitles = compressed_subtitles + other_subtitles

    headers = ["Index", "Name", "Format"]
    header_line = f"{Fore.YELLOW}{headers[0].ljust(6)}{headers[1].ljust(50)}{headers[2].ljust(10)}"
    print(header_line)
    print(Fore.YELLOW + "-" * len(header_line))

    for idx, (name, link) in enumerate(sorted_subtitles, start=1):
        format = "Compressed" if any(ext in name.lower() for ext in ['.zip', '.rar']) else "Other"
        color = Fore.GREEN if format == "Compressed" else Fore.CYAN

        if len(name) > title_space:
            name = name[:title_space-3] + "..."

        line = f"{color}{str(idx).ljust(6)}{name.ljust(50)}{format.ljust(10)}"
        print(line)
    return sorted_subtitles

def search_kitsunekko(anime_name_romaji):
    base_url = 'https://kitsunekko.net/'
    url = f'https://kitsunekko.net/dirlist.php?dir=subtitles%2Fjapanese%2F'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    found_href = []
    for row in soup.find_all('tr'):
        a_tag = row.find('a')
        if a_tag and 'href' in a_tag.attrs:
            subname =  a_tag.text.strip()
            if fuzz.ratio(subname.lower(), anime_name_romaji.lower()) > 70: 
                found_href.append((subname, base_url + a_tag['href']))

    if not found_href:
        print(Fore.RED + "No subtitles found.")
        return []
    
    for idx, (subname, href) in enumerate(found_href, start=1):
        print(Fore.BLUE + f"{idx}. {subname}")

    selected_index = input(Fore.BLUE + "Enter the number of the subtitle folder you want to explore: ")
    try:
        selected_index = int(selected_index) - 1
        if selected_index < 0 or selected_index >= len(found_href):
            raise ValueError
    except ValueError:
        print(Fore.RED + "Invalid selection.")
        return []

    selected_folder_url = found_href[selected_index][1]
    response = requests.get(selected_folder_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    subtitles = []
    for idx, row in enumerate(soup.find_all('tr'), start=1):
        a_tag = row.find('a')
        if a_tag and 'href' in a_tag.attrs:
            subtitle_link = base_url + a_tag['href']
            subtitle_name = a_tag.text.strip()
            subtitles.append((subtitle_name, subtitle_link))
    
    sorted_subtitles = display_subtitles_in_table(subtitles)
        
    selected_subtitles_indices = input(Fore.BLUE + "Enter the number(s) of the subtitles you want to download (e.g., 1, 3, 5): ")
    selected_subtitles_indices = selected_subtitles_indices.split(',')

    download_links = []
    for index in selected_subtitles_indices:
        try:
            idx = int(index.strip()) - 1
            if 0 <= idx < len(sorted_subtitles):
                download_links.append(sorted_subtitles[idx][1])
            else:
                print(Fore.RED + f"No subtitle found for selection {index}.")
        except ValueError:
            print(Fore.RED + f"Invalid selection: {index}.")

    return download_links

def move_files_up_and_remove_dir(dir_path, target_path):
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        target_item_path = os.path.join(target_path, item)
        if os.path.isdir(item_path):
            for file in os.listdir(item_path):
                shutil.move(os.path.join(item_path, file), os.path.join(target_path, file))
            os.rmdir(item_path)
        else:
            shutil.move(item_path, target_item_path)
    os.rmdir(dir_path)

def get_current_directories(path):
    return {item for item in os.listdir(path) if os.path.isdir(os.path.join(path, item))}

def download_and_extract_subtitle(download_link, download_path):
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    pre_extraction_dirs = get_current_directories(download_path)
    filename = download_link.split('/')[-1]
    file_path = os.path.join(download_path, filename)
    with requests.get(download_link, stream=True) as r, open(file_path, 'wb') as file:
        shutil.copyfileobj(r.raw, file)

    if file_path.endswith('.zip') or file_path.endswith('.rar'):
        with zipfile.ZipFile(file_path, 'r') if file_path.endswith('.zip') else rarfile.RarFile(file_path, 'r') as archive_ref:
            archive_ref.extractall(download_path)
        os.remove(file_path) 

        post_extraction_dirs = get_current_directories(download_path)
        new_dirs = post_extraction_dirs - pre_extraction_dirs

        for dir_name in new_dirs:
            dir_path = os.path.join(download_path, dir_name)
            print(dir_path)
            move_files_up_and_remove_dir(dir_path, download_path)

def sort_nicely(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    l.sort(key=alphanum_key)

def prompt_filter_files(vid_files, sub_files):
    common_filters = ['OVA', 'Special', 'NCED', 'NCOP', 'SP']
    for term in common_filters:
        vid_files = [video for video in vid_files if term.lower() not in video.lower()]
        sub_files = [sub for sub in sub_files if term.lower() not in sub.lower()]
    return vid_files, sub_files

def reani(path):
    sub_extension = input("Extension of subtitle files (ex: .sub, .srt, etc): ")
    vid_files = [name for name in os.listdir(path) if name.endswith(('.mp4', '.mkv', '.avi'))]
    sub_files = [name for name in os.listdir(path) if name.endswith(sub_extension)]
    print(len(sub_files))
    if len(sub_files) < len(vid_files):
        print(Fore.YELLOW + "There are fewer subtitle files than video files.")
        vid_files, sub_files = prompt_filter_files(vid_files, sub_files)
        print(len(sub_files))
        if len(sub_files) < len(vid_files):
            user_choice = input(Fore.YELLOW + "Subtitles are still short. Do you want to proceed with renaming anyway? [y/n]: ")
            if user_choice.lower() != 'y':
                print(Fore.RED + "Renaming cancelled by user.")
                return

    elif len(sub_files) > len(vid_files):
        print(Fore.RED + "There are more subtitle files than video files. Please adjust manually.")
        return

    sort_nicely(vid_files)
    sort_nicely(sub_files)
    os.chdir(path)

    for i, video_name in enumerate(vid_files):
        if i < len(sub_files):
            new_sub_name = os.path.splitext(video_name)[0] + sub_extension
            print(f"Renaming '{sub_files[i]}' to '{new_sub_name}'")
            os.rename(sub_files[i], new_sub_name)
        else:
            print(Fore.YELLOW + f"Missing subtitle for '{video_name}'. No more subtitles to rename.")
            break
    print(Fore.GREEN + 'Done renaming!')

def main(download_anime=None, skip_subs=False, quality='1080p', batch=False, reani_path=None, quicksub=None, quicksub_path=None):
    if download_anime:
        anime_info = search_anilist(download_anime)
        
        if anime_info:
            print(f"Found Anime: {anime_info['title_romaji']} ({anime_info['title_native']})")
            print(f"Cover Image: {anime_info['cover_image']}")
        else:
            print("Anime not found.")
            exit()
        if not batch and not anime_info['status'] == "FINISHED":
            search_result = search_nyaa(anime_info['title_romaji'] + quality)
        else:
            search_result = search_nyaa(anime_info['title_romaji'] + ' batch' + " " + quality)
        
        save_path = os.path.join("D:\\ビデオ\\アニメ", anime_info['title_native'])

        selected_torrents = display_and_select_torrents(search_result['data'])
        for torrent in selected_torrents:
            magnet_link = torrent['magnet']
            download_torrent(magnet_link, anime_info['title_native'], save_path)
        
        if skip_subs: 
            print('skip-sub enabled: Skipping subs and exiting...')
            exit()
        download_links = search_kitsunekko(anime_info['title_romaji'])
        for link in download_links:
            download_and_extract_subtitle(link, save_path)
    elif quicksub:
        download_links = search_kitsunekko(quicksub)
        for link in download_links:
            download_and_extract_subtitle(link, quicksub_path)
    elif reani_path:
        reani(reani_path)

def super_ani_handle():
    parser = argparse.ArgumentParser(description="Anime Downloader and Subtitle Renamer")
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument("-d", "--download", dest="download_anime", help="Download anime by name", type=str)
    group.add_argument('--reani', '-r', type=str, nargs='?', const=os.getcwd(), help="Run the reani function to rename subtitles")
    group.add_argument('--quicksub', '-k', type=str, nargs='+', help="Search for subtitles only")
    
    parser.add_argument("--skip-subs", '-s', help="Skip downloading subtitles", action="store_true", default=False)
    parser.add_argument('--quality', '-q', choices=['720p', '1080p'], default='1080p', help="Quality of the anime to download")
    parser.add_argument("--batch", '-b', action="store_true", help="Force batch download, regardless of airing status")
    args = parser.parse_args()
    if args.reani:
        main(reani_path=args.reani)
    elif args.quicksub:
        main(quicksub=args.quicksub[0], quicksub_path=args.quicksub[1])
    else:
        main(download_anime=args.download_anime, skip_subs=args.skip_subs, quality=args.quality, batch=args.batch)