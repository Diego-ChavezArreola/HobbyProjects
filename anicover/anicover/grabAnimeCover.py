import json
import os
import requests
import logging
import ctypes
from ctypes import POINTER, Structure, c_wchar, c_int, sizeof, byref
from ctypes.wintypes import BYTE, WORD, DWORD, LPWSTR
import win32api
from tqdm import tqdm
from PIL import Image

try:
    from fuzzywuzzy import fuzz
except ImportError:
    raise ImportError("Please install fuzzywuzzy for fuzzy search: pip install fuzzywuzzy[speedup]")

###############################################################################
# GLOBAL CONFIGURATION
###############################################################################
IGNORE_FILES = {'desktop.ini', '映画', 'ICO', 'ICO_NEW', 'ICO_OLD', 'auto-sub-retimer'}
CACHE_FILE = 'anilist_cache.json'  # to store AniList search results locally

ICON_OUTPUT_DIRECTORY = r"PATH TO YOUR ICON FOLDER"

ANIME_PATH = r"PATH TO YOUR ANIME FOLDER"

SHOKO_API_KEY = 'YOUR_SHOKO_API_KEY'

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

###############################################################################
# WIN32 ICON SETUP
###############################################################################
HICON = c_int
LPTSTR = LPWSTR
TCHAR = c_wchar
MAX_PATH = 260
FCSM_ICONFILE = 0x00000010
FCS_FORCEWRITE = 0x00000002
SHGFI_ICONLOCATION = 0x000001000

class GUID(Structure):
    _fields_ = [
        ('Data1', DWORD),
        ('Data2', WORD),
        ('Data3', WORD),
        ('Data4', BYTE * 8),
    ]

class SHFOLDERCUSTOMSETTINGS(Structure):
    _fields_ = [
        ('dwSize', DWORD),
        ('dwMask', DWORD),
        ('pvid', POINTER(GUID)),
        ('pszWebViewTemplate', LPTSTR),
        ('cchWebViewTemplate', DWORD),
        ('pszWebViewTemplateVersion', LPTSTR),
        ('pszInfoTip', LPTSTR),
        ('cchInfoTip', DWORD),
        ('pclsid', POINTER(GUID)),
        ('dwFlags', DWORD),
        ('pszIconFile', LPTSTR),
        ('cchIconFile', DWORD),
        ('iIconIndex', c_int),
        ('pszLogo', LPTSTR),
        ('cchLogo', DWORD),
    ]

class SHFILEINFO(Structure):
    _fields_ = [
        ('hIcon', HICON),
        ('iIcon', c_int),
        ('dwAttributes', DWORD),
        ('szDisplayName', TCHAR * MAX_PATH),
        ('szTypeName', TCHAR * 80),
    ]

def seticon(folderpath, iconpath, iconindex=0):
    """Set the folder icon for 'folderpath' to 'iconpath'."""
    shell32 = ctypes.windll.shell32

    folderpath = os.path.abspath(folderpath)
    iconpath = os.path.abspath(iconpath)

    fcs = SHFOLDERCUSTOMSETTINGS()
    fcs.dwSize = sizeof(fcs)
    fcs.dwMask = FCSM_ICONFILE
    fcs.pszIconFile = iconpath
    fcs.cchIconFile = 0
    fcs.iIconIndex = iconindex

    hr = shell32.SHGetSetFolderCustomSettings(
        byref(fcs),
        folderpath,
        FCS_FORCEWRITE
    )
    if hr:
        raise WindowsError(win32api.FormatMessage(hr))

    sfi = SHFILEINFO()
    hr = shell32.SHGetFileInfoW(
        folderpath,
        0,
        byref(sfi),
        sizeof(sfi),
        SHGFI_ICONLOCATION
    )
    if hr == 0:
        raise WindowsError(win32api.FormatMessage(hr))


###############################################################################
# IMAGE UTILS
###############################################################################
def expand_to_square(img, background_color=(0, 0, 0, 0)):
    """Centers the image onto a square background."""
    width, height = img.size
    if width == height:
        return img
    elif width > height:
        new_image = Image.new(img.mode, (width, width), background_color)
        new_image.paste(img, (0, (width - height) // 2))
        return new_image
    else:
        new_image = Image.new(img.mode, (height, height), background_color)
        new_image.paste(img, ((height - width) // 2, 0))
        return new_image


def convert_png_to_ico(png_file, output_dir=ICON_OUTPUT_DIRECTORY):
    """Converts a PNG file to ICO and saves it into output_dir."""
    file_base = os.path.splitext(os.path.basename(png_file))[0]
    file_icon = os.path.join(output_dir, file_base + '.ico')

    img = Image.open(png_file).convert("RGBA")
    fixed_image = expand_to_square(img, (0, 0, 0, 0))
    fixed_image.save(file_icon, format='ICO', sizes=[(256, 256)])

    return file_icon


###############################################################################
# ANILIST API LOGIC
###############################################################################
ANILIST_URL = 'https://graphql.anilist.co'
session = requests.Session()

QUERY = '''
query ($page: Int, $perpage: Int, $search: String){
  Page (page: $page, perPage: $perpage){
    pageInfo{
      total
      currentPage
      lastPage
      hasNextPage
      perPage
    }
    media(search: $search, type: ANIME){
      id
      title {
        romaji
        english
        native
      }
      coverImage {
        extraLarge
      }
    }
  }
}
'''

def load_cache():
    """Load the AniList search cache from a file."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache(cache_data):
    """Save the AniList search cache to a file."""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=4, ensure_ascii=False)

def fetch_anilist_data(anime_name):
    """
    Fetch possible matches from AniList for the given anime_name.
    Returns a list of anime dicts with (id, title, coverImage).
    """
    variables = {
        'search': anime_name,
        'page': 1,
        'perpage': 10  
    }

    try:
        response = session.post(
            ANILIST_URL,
            json={'query': QUERY, 'variables': variables}
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error fetching from AniList: {e}")
        return []

    data = response.json()

    media_list = data.get('data', {}).get('Page', {}).get('media', [])
    if not media_list:
        logger.debug(f"No results found in AniList for '{anime_name}'")
        return []
    return media_list

def get_best_match(media_list, folder_name):
    """
    Given a list of AniList media results and a folder name,
    pick the best match using fuzzy matching of the folder name
    against each media's title fields.
    """
    best_score = 0
    best_match = None

    for media_item in media_list:
        possible_titles = []
        t = media_item.get("title", {})
        if t.get("romaji"):
            possible_titles.append(t["romaji"])
        if t.get("english"):
            possible_titles.append(t["english"])
        if t.get("native"):
            possible_titles.append(t["native"])

        for title in possible_titles:
            score = fuzz.partial_ratio(folder_name.lower(), title.lower())
            if score > best_score:
                best_score = score
                best_match = media_item

    if best_match:
        logger.debug(
            f"Best fuzzy match for '{folder_name}' is '{best_match['title']} (score={best_score})'"
        )
    return best_match

def grab_cover_url(anime_name):
    """
    High-level function:
    - Checks cache first
    - If not found, fetches from AniList
    - Uses fuzzy matching to pick best media entry
    - Returns the coverImage URL for that entry
    """
    cache = load_cache()
    if anime_name in cache:
        logger.debug(f"Found '{anime_name}' in local cache.")
        return cache[anime_name]

    media_list = fetch_anilist_data(anime_name)
    if not media_list:
        logger.warning(f"No AniList results for '{anime_name}'")
        return None

    best_match = get_best_match(media_list, anime_name)
    if not best_match:
        logger.warning(f"No best match for '{anime_name}' after fuzzy search.")
        return None

    cover_url = best_match.get("coverImage", {}).get("extraLarge")
    if not cover_url:
        logger.warning(f"No coverImage URL found for '{anime_name}'")
        return None

    cache[anime_name] = cover_url
    save_cache(cache)
    return cover_url

def download_and_convert_cover(anime_name):
    """
    Downloads the best matched cover from AniList, saves to PNG,
    converts to ICO, and returns the path to the ICO file.
    """
    url = grab_cover_url(anime_name)
    if not url:
        logger.error(f"Unable to find or download a cover for '{anime_name}'.")
        return None

    if not os.path.exists(ICON_OUTPUT_DIRECTORY):
        os.makedirs(ICON_OUTPUT_DIRECTORY, exist_ok=True)

    local_png_path = os.path.join(ICON_OUTPUT_DIRECTORY, anime_name + '.png')
    try:
        resp = session.get(url)
        resp.raise_for_status()
        with open(local_png_path, 'wb') as f:
            f.write(resp.content)
        logger.debug(f"Saved cover to '{local_png_path}'")
    except requests.RequestException as e:
        logger.error(f"Failed to download cover for '{anime_name}': {e}")
        return None

    # Convert to ICO
    try:
        icon_path = convert_png_to_ico(local_png_path, ICON_OUTPUT_DIRECTORY)
        logger.debug(f"Converted to ICO: '{icon_path}'")
    except Exception as e:
        logger.error(f"Failed to convert PNG to ICO for '{anime_name}': {e}")
        return None

    return icon_path

###############################################################################
# MAIN HANDLER
###############################################################################
def anime_folder(anime_path):
    """
    Iterates through all directories in anime_path, ignoring IGNORE_FILES,
    downloading covers, converting to icons, and setting the icon.
    """
    folder_names = os.listdir(anime_path)
    folders_to_process = [
        f for f in folder_names
        if f not in IGNORE_FILES
        and '.parts' not in f
        and os.path.isdir(os.path.join(anime_path, f))
    ]

    logger.info(f"Processing {len(folders_to_process)} folders in '{anime_path}'")

    updated_count = 0
    with tqdm(total=len(folders_to_process), desc="Updating icons") as pbar:
        for anime in folders_to_process:
            real_path = os.path.join(anime_path, anime)
            existing_ico_path = os.path.join(ICON_OUTPUT_DIRECTORY, anime + '.ico')

            if os.path.exists(existing_ico_path):
                icon_path = existing_ico_path
                logger.debug(f"Reusing existing icon for '{anime}'")
            else:
                logger.debug(f"Downloading and converting cover for '{anime}'")
                icon_path = download_and_convert_cover(anime)

            if icon_path and os.path.exists(icon_path):
                try:
                    seticon(real_path, icon_path)
                    updated_count += 1
                except WindowsError as e:
                    logger.error(f"Failed to set icon for '{anime}': {e}")
            else:
                logger.warning(f"Skipping icon set for '{anime}' due to missing icon")

            pbar.update(1)

    logger.info(f"Successfully updated {updated_count} anime covers out of {len(folders_to_process)}!")

def mainHandler():
    """
    Entry point if you want to run this script directly.
    """
    anime_folder(ANIME_PATH)

