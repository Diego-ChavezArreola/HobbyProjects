import uuid
import certifi
import datetime
from pymongo import MongoClient

from .prompts import ask_pass, ask_user, new_note_dict
from .ankiconnect import invoke
from .config import return_config, write_config


# Login to MongoDB
def mongoAuth(username, password):
    ca = certifi.where()
    cluster = MongoClient(
        f"mongodb+srv://{username}:{password}@ankibuddy-cluster.6krdi.mongodb.net/anki?retryWrites=true&w=majority",
        tlsCAFile=ca
    )
    db = cluster["anki"]
    db.command("ping")
    return db["notes"]


# Returns Collection
def mongo_db_login():
    settings = return_config()
    while True:
        try:
            collection = mongoAuth(
                settings["user_settings"]["username"],
                settings["user_settings"]["password"],
            )
            return settings, collection
        except Exception as e:
            if e.code:
                if e.code == 8000:
                    print('Wrong username or password!')
                    settings["user_settings"]["username"] = ask_user()[
                        "username"]
                    settings["user_settings"]["password"] = ask_pass()[
                        "password"]
                    write_config(settings)
                    continue
            else:
                print("There was a problem with mongodb")
                print(e)
                exit()


# Basic media field formatter, works for img and sound nothing else
def format_media_field(field):
    if "<img" in field:
        return field.split('src="')[1].split('"')[0]
    elif "[sound:" in field:
        return field.split(":")[1].split("]")[0]
    return None


def clean_img_field(image):
    return f'<img alt="snapshot" src="{image}">'


def note_to_json(note_id, settings):
    curr_note = invoke("notesInfo", notes=note_id)

    # I hope you know list comprehension :)
    media_fields = [
        r
        for r in (
            format_media_field(curr_note[0]["fields"][field]["value"])
            for field in curr_note[0]["fields"]
        )
        if r is not None
    ]
    field_dict = {
        k: (
            curr_note[0]["fields"][k]["value"]
            if not "<img" in curr_note[0]["fields"][k]["value"]
            else clean_img_field(format_media_field(curr_note[0]["fields"][k]["value"]))
        )
        for k in curr_note[0]["fields"]
    }
    base64_media = invoke(
        "multi",
        actions=[
            {"action": "retrieveMediaFile", "params": {"filename": file_name}}
            for file_name in media_fields
        ],
    )
    media_dict = {k: v for (k, v) in zip(media_fields, base64_media)}

    note_dict = {
        "deckName": settings["user_settings"]["deckName"],
        "modelName": curr_note[0]["modelName"],
        "fields": field_dict,
        "options": settings["options"],
        "tags": ["ankibuddy"],
        "media": media_dict,
    }
    return note_dict


def get_last_note(settings):
    return note_to_json([invoke("findNotes", query=f"added:1")[-1]], settings)


# adds last note to mongodb
def mongo_db_add(collection, settings):
    time_stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S-") + str(
        uuid.uuid4()
    )
    note = {"_id": time_stamp, **get_last_note(settings)}
    collection.insert_one(note)


# main function that sends note to mongoDB
def send_note(num=None):
    settings, collection = mongo_db_login()
    if num is None:
        mongo_db_add(collection, settings)
    print("Note uploaded to database!")


# takes a note form mongo db and pops it into anki
def add_note_anki(settings, note, note_key):
    media = note["media"]
    note["modelName"] = settings["user_settings"]["modelName"]
    note["deckName"] = settings["user_settings"]["deckName"]
    note.pop("_id")
    note.pop("media", None)

    for key, value in settings["note_dict"][note_key].items():
        if value == "(None)":
            note["fields"].pop(key)
            continue
        note["fields"][value] = note["fields"].pop(key)

    actions_op = [
        {"action": "storeMediaFile", "params": {"filename": key, "data": value}}
        for key, value in media.items()
    ]
    actions_op.append({"action": "addNote", "params": {"note": note}})
    invoke("multi", actions=actions_op)


def get_latest(collection):
    last_added = collection.find().sort("_id", -1)
    return last_added


def note_dict_handle(settings, note, note_key, new_note=False):
    if new_note:
        settings["note_dict"][note_key] = new_note_dict(settings, note)
        write_config(settings)
    add_note_anki(settings, note, note_key)


# main function for downloading from our DB
def download_note(num=None, grab_all=False):
    settings, collection = mongo_db_login()
    notes = list(get_latest(collection))
    note_key = f"{notes[0]['modelName']}::{settings['user_settings']['modelName']}"
    # makes new note_dict if needed in settings.json then adds note to anki
    if not settings["note_dict"]:
        note_dict_handle(settings, notes[0], note_key, new_note=True)
    else:
        if note_key in settings["note_dict"].keys():
            note_dict_handle(settings, notes[0], note_key)
        else:
            note_dict_handle(settings, notes[0], note_key, new_note=True)
    print("Most recently added note downloaded and added!")
