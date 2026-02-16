import qbittorrentapi as qb
import requests
import json

qbt_client = qb.Client(host='localhost', port='8080', username='admin', password='password')

try:
    qbt_client.auth_log_in()
except qb.LoginFailed as e:
    print(e)
    
    
def grab_tags(anime_name):
    query ='''
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
                genres
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

    response = requests.post(url, json={'query': query, 'variables':variables})
    response.raise_for_status()
    data = response.json()

    search_file = json.dumps(data, indent=4)
    json_file = json.loads(search_file)
    ##Returns the link and only the link
    try:
        return(json_file['data']['Page']['media'][0]['genres'])
    except:
        print(fr'{anime_name} Caused and error! Fix the title or add to the IGNORE_FILE list!')
        exit()    
    
    
for torrents in qbt_client.torrents_info():
    if torrents['category'] == 'アニメ「TV」':
        tag_list = grab_tags(torrents['name'])
        qbt_client.torrents_add_tags(tags=tag_list, torrent_hashes=torrents['hash'])
        
        
        
        
