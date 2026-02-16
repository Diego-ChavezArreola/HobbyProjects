import json
import urllib.request
import os
import base64
from .config import read_config
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from io import BytesIO
from zipfile import ZipFile


#gets fields from config file and ID of shared google drive folder
FIELDS, SHARED_FOLDER  = read_config()

#makes a note object given data either from the reciver or sender class 
class Note:
    def __init__(self, data):
        self.note_id, self.note_array = (data[0]['noteId'], self.makeNote(data)) if isinstance(data[0], dict) else (None, data[:-1])
        self.focus_word, self.sent, self.translation, self.definition, self.image, self.sent_audio, self.vocab_audio = [elm for elm in self.note_array]
        self.files = [self.image, self.sent_audio, self.vocab_audio]
        
    def makeNote(self, data):
        if not data[0]['modelName'] == FIELDS[7]:
            print('The last card you made is not the configured model name!')
            exit()
        note_array = [self.format_field(data[0]['fields'][field]['value']) for field in FIELDS[:-2]]
        return note_array
        
    #checks if the image field or sound field is empty before split
    def format_field(self, field):
        if '<img' in field:
            return field.split('src="')[1].split('"')[0]
        elif '[sound:' in field:
            return field.split(":")[1].split(']')[0]
        return field

#creates package from last added anki note and uploades it to shared drive folder
class Sender:
    def __init__(self, service, temp_dir):
        self.note_data = invoke('notesInfo', notes=[invoke('findNotes', query='added:1')[-1]])
        self.note = Note(self.note_data)
        self.note_path = self.note_to_txt(temp_dir)
        self.zip_path = self.zip_files(self.note_path, temp_dir)
        self.file_id = self.upload_note(service, self.zip_path)
        
    def note_to_txt(self, temp_dir):
        note_path = f'{temp_dir}\\note.txt'
        note_text = open(note_path, 'w', encoding='utf-8')
        
        for elm in self.note.note_array:
            note_text.write(elm + ';;')
        note_text.close()
        
        return note_path

    #zips files from note.file_list and calls the get_media function
    def zip_files(self, note_path, temp_dir):
        zip_path = f'{temp_dir}\\note{self.note.note_id}.zip'
        
        noteZip = ZipFile(zip_path, 'w')
        noteZip.write(note_path, os.path.basename(note_path))
        paths = self.get_media(self.note.files, temp_dir)
        
        for path in paths:
            noteZip.write(path, os.path.basename(path))
        noteZip.close()
        
        return zip_path

    #upload to google_drive and return uploaded files id
    def upload_note(self, service, zip_dir):
        file_metadata = {
            'name': f'note{self.note.note_id}.zip',
            'parents': [SHARED_FOLDER]}
        try:
            media = MediaFileUpload(
                zip_dir,
                mimetype='application/zip')
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            return file.get('id')
        except FileNotFoundError:
            print("Missing media! Your zip file wasn't created properly")

    #makes a multi action and invokes ankiconnect returns list of paths
    def get_media(self, file_names, temp_dir):
        actions_op = [{'action': 'retrieveMediaFile', 'params':{'filename':file_name}} for file_name in file_names]
        files = invoke('multi', actions=actions_op)
        
        for file_64, file_name in zip(files, file_names):
            file = open(f'{temp_dir}\\{file_name}', 'wb')
            file.write(base64.b64decode(file_64))
            file.close()
            
        return [f'{temp_dir}\\{file_name}' for file_name in file_names]



#either takes a file_id or gets the last uploaded file_id and downloades and makes into anki card
class Receiver:
    def __init__(self, service, temp_dir, file_id=None, num_files=1):
        self.file_id, self.file_name = self.get_last_note_drive(service) if file_id == None else (file_id, service.files().get(fileId=file_id).execute().get('name'))
        self.drive_download(service, temp_dir)
        self.unzip(temp_dir)
        self.note = Note(self.note_txt(temp_dir))
        self.store_file_and_addnote(temp_dir)

    def drive_download(self, service, temp_dir):
        media_request = service.files().get_media(fileId=self.file_id)
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, media_request)
        done = False
        
        while done is False:
            done = downloader.next_chunk()
            
        fh.seek(0)
        
        with open(f'{temp_dir}\\{self.file_name}', 'wb') as f:
            f.write(fh.read())
            f.close()

    def unzip(self, temp_dir):
        with ZipFile(f'{temp_dir}\\{self.file_name}', 'r') as zip_f:
            zip_f.extractall(temp_dir)

    def note_txt(self, temp_dir):
        note_text = open(f'{temp_dir}\\note.txt', 'r', encoding='utf-8')
        data = note_text.read().split(";;")
        return data

    def store_file_and_addnote(self, temp_dir):
        path_list = [f'{temp_dir}\\{file}' for file in self.note.files]
        options_op = {
            "allowDuplicate": False,
            "duplicateScope": "deck",
            "duplicateScopeOptions": {
                "deckName": "Default",
                "checkChildren": False,
                "checkAllModels": False}}
        note_op = {
            'deckName': FIELDS[8],
            'modelName': FIELDS[7],
            'fields': {
                FIELDS[0]: self.note.focus_word,
                FIELDS[1]: self.note.sent,
                FIELDS[2]: self.note.translation,
                FIELDS[3]: self.note.definition,
                FIELDS[4]: f'<img alt="snapshot" src="{self.note.image}">',
                FIELDS[5]: f'[sound:{self.note.sent_audio}]',
                FIELDS[6]: f'[sound:{self.note.vocab_audio}]',
                'options': options_op,
                'tags': 'ankibuddy'}}
        actions_op = [{'action': 'storeMediaFile', 'params':{'filename':file_name, 'path':path}} for file_name, path in zip(self.note.files, path_list)]
        actions_op.append({'action': 'addNote', 'params': {'note': note_op}})
        invoke('multi', actions=actions_op)

    def get_last_note_drive(self, service):
        query = f"parents = '{SHARED_FOLDER}'"
        param = {'orderBy': 'createdTime', 'q': query} 
        response = service.files().list(**param).execute()
        file = response.get('files')
        nextPageToken = response.get('nextPageToken')
        while nextPageToken:
            response = service.files().list(pageToken=nextPageToken, **param).execute()
            file.extend(response.get('files'))
            nextPageToken = response.get('nextPageToken')
        
        return (file[-1]['id'], file[-1]['name'])

# Formats our request
def request(action, **params):
    return {'action': action, 'params': params, 'version': 6}

# Invokes ankiconnect and returns the result
def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode('utf-8')
    response = json.load(
        urllib.request.urlopen(
            urllib.request.Request(
                'http://localhost:8765',
                requestJson)))
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']

