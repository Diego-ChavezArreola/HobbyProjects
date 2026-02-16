from __future__ import print_function, unicode_literals

import json
import os

from .ankiconnect import invoke
from .prompts import ask_user, ask_pass, ask_deck, ask_model, ask_menu

settings_dir_path = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)),
                 "..", "settings.json")
)


# This makes a fresh config from scratch
def make_config():
    print("Making a fresh config...")
    result = invoke(
        "multi", actions=[{"action": "deckNames"}, {"action": "modelNames"}]
    )
    deck_list = result[0]
    model_list = result[1]
    username = ask_user()
    password = ask_pass()
    deck = ask_deck(deck_list)
    model, field_list = ask_model(model_list, return_fields=True)

    settings_dict = {
        "user_settings": {
            "username": username["username"],
            "password": password["password"],
            "deckName": deck["deckName"],
            "modelName": model["modelName"],
        },
        "options": {
            "allowDuplicate": False,
            "duplicateScope": "deck",
            "duplicateScopeOptions": {
                "deckName": "Default",
                "checkChildren": False,
                "checkAllModels": False,
            },
        },
        "note_settings": {"curr_fields": field_list},
        "note_dict": {},
    }
    write_config(settings_dict)
    print("Made new config file. Use -c or --config to change it.")
    return settings_dict


# Config changing menu and logic
def change_config():
    if not os.path.exists(settings_dir_path):
        make_config()
        return
    curr_config = read_config()
    while True:
        result = ask_menu(curr_config)
        if result == "exit":
            write_config(curr_config)
            break

        options = {"username": ask_user,
                   "password": ask_pass, "deckName": ask_deck}
        if result == "modelName":
            ask_result, field_list = ask_model(return_fields=True)
            curr_config["note_settings"]["curr_fields"] = field_list
        else:
            ask_result = options[result]()

        curr_config["user_settings"][result] = ask_result[result]


# reads existing config returns dict
def read_config():
    with open(settings_dir_path, "r") as f:
        settings = json.load(f)
        f.close()
    return settings


# writes settings given the new settings then returns
def write_config(new_settings):
    with open(settings_dir_path, "w") as f:
        json.dump(new_settings, f, indent=4)
        f.close()
    return


# Checks if config exits then returns new or existing config as dict.
def return_config():
    if os.path.exists(settings_dir_path):
        return read_config()
    else:
        return make_config()
