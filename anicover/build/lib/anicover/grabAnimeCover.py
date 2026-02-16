import json
from os import listdir
import requests
from PIL import Image
from os.path import exists
import os
import ctypes
from ctypes import POINTER, Structure, c_wchar, c_int, sizeof, byref
from ctypes.wintypes import BYTE, WORD, DWORD, LPWSTR, LPSTR
import win32api
from tqdm import tqdm
import logging


# Files we don't want the program to change the icon for
IGNORE_FILES = ['desktop.ini', '映画', 'ICO', 'ICO_NEW', 'ICO_OLD', 'auto-sub-retimer']
# Everything for changing the icon
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
        ('Data4', BYTE * 8)]


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
        ('cchLogo', DWORD)]


class SHFILEINFO(Structure):
    _fields_ = [
        ('hIcon', HICON),
        ('iIcon', c_int),
        ('dwAttributes', DWORD),
        ('szDisplayName', TCHAR * MAX_PATH),
        ('szTypeName', TCHAR * 80)]


def seticon(folderpath, iconpath, iconindex):

    shell32 = ctypes.windll.shell32

    folderpath = os.path.abspath(folderpath)
    iconpath = os.path.abspath(iconpath)

    fcs = SHFOLDERCUSTOMSETTINGS()
    fcs.dwSize = sizeof(fcs)
    fcs.dwMask = FCSM_ICONFILE
    fcs.pszIconFile = iconpath
    fcs.cchIconFile = 0
    fcs.iIconIndex = iconindex

    hr = shell32.SHGetSetFolderCustomSettings(byref(fcs), folderpath,
                                              FCS_FORCEWRITE)
    if hr:
        raise WindowsError(win32api.FormatMessage(hr))

    sfi = SHFILEINFO()
    hr = shell32.SHGetFileInfoW(folderpath, 0, byref(sfi), sizeof(sfi),
                                SHGFI_ICONLOCATION)
    if hr == 0:
        raise WindowsError(win32api.FormatMessage(hr))
# END Of Icon Changing Stuff

# Centers the cover image/makes it into a square with transparent padding


def expandToSquare(img, background_color):
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

# Converts from png to icon


def convertPng(cover_image):
    file_icon = cover_image[:-4] + r'.ico'
    img = Image.open(cover_image)
    rgba = img.convert("RGBA")
    fixed_image = expandToSquare(rgba, (0, 0, 0, 0))
    fixed_image.save(file_icon, format='ICO', sizes=[(256, 256)])
    return file_icon

# Uses anilist.co api to grab extra large cover link


def grab_link(anime_name):
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

    query = '''
    query ($id: Int, $page: Int, $perpage: Int, $search: String){
        Page (page: $page, perPage: $perpage){
            pageInfo{
                total
                currentPage
                lastPage
                hasNextPage
                perPage
            }
            media(id: $id, search: $search, type: ANIME){
                id
                title{
                    romaji
                    english
                    native
                }
                coverImage{
                    extraLarge
                }
            }
        }
    }
    '''
    variables = {
        'search': anime_name,
        'page': 1,
        'perpage': 1
    }
    url = 'https://graphql.anilist.co'

    response = requests.post(
        url, json={'query': query, 'variables': variables})
    response.raise_for_status()
    data = response.json()

    search_file = json.dumps(data, indent=4)
    json_file = json.loads(search_file)
    # Returns the link and only the link
    try:
        return(json_file['data']['Page']['media'][0]['coverImage']['extraLarge'])
    except:
        print(
            fr'{anime_name} Caused and error! Fix the title or add to the IGNORE_FILE list!')
        exit()

# Downloades the cover


def download_cover(anime_name, download_location):
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True
    url = grab_link(anime_name)
    local_filename = download_location + '\\' + anime_name + r'.png'
    r = requests.get(url)
    with open(local_filename, 'wb') as f:
        f.write(r.content)
        return convertPng(local_filename)

# This is basically our main


def anime_folder(anime_path):
    anime_count = 0
    folder_names = listdir(anime_path)
    with tqdm(total=len(folder_names) - len(IGNORE_FILES) - 1) as pbar:
        for anime in folder_names:
            if(anime not in IGNORE_FILES and '.parts' not in anime):
                real_path = anime_path + '/' + anime
                temp_path = 'D:\ビデオ\アニメ\ICO_NEW' + '\\' + anime + '.ico'
                if exists(temp_path):
                    icon_path = temp_path
                else:
                    icon_path = download_cover(anime, 'D:\\ビデオ\\アニメ\\ICO_NEW')
                seticon(real_path, icon_path, 0)
                anime_count += 1
                pbar.update(1)

    print(fr'Successfully updated {anime_count} anime covers!')


def mainHandler():
    anime_path = 'D:\ビデオ\アニメ'
    anime_folder(anime_path)
