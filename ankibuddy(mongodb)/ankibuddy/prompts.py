from .ankiconnect import invoke
from PyInquirer import prompt

from colorama import Fore
from colorama import init as colorama_init

colorama_init(autoreset=True)


def ask_user():
    questions = [
        {"type": "input", "name": "username", "message": "Enter username to MongoDB"}
    ]
    answer = prompt(questions)
    return answer


def ask_pass():
    questions = [
        {"type": "password", "name": "password", "message": "Enter password to MongoDB"}
    ]
    answer = prompt(questions)
    return answer


def ask_deck(deck_list=None):
    if not deck_list:
        deck_list = invoke("deckNames")
    questions = [
        {
            "type": "list",
            "name": "deckName",
            "message": "Which deck would you like ankibuddy to import into",
            "choices": deck_list,
        }
    ]
    answer = prompt(questions)
    return answer


def ask_model(model_list=None, return_fields=False):
    if not model_list:
        model_list = invoke("modelNames")
    questions = [
        {
            "type": "list",
            "name": "modelName",
            "message": "What model would you like to use",
            "choices": model_list,
        }
    ]
    answer = prompt(questions)
    if return_fields:
        field_list = invoke("modelFieldNames", modelName=answer["modelName"])
        return answer, field_list
    return answer


def ask_menu(settings):
    options = {0: "username", 1: "password", 2: "deckName", 3: "modelName", 4: "exit"}
    choices = [
        f"Username:{settings['user_settings']['username']}",
        "Password:******",
        f"Import Deck:{settings['user_settings']['deckName']}",
        f"Import Model:{settings['user_settings']['modelName']}",
        "Save and Exit",
    ]
    questions = [
        {
            "type": "list",
            "name": "menu_answer",
            "message": "What would you like to change?",
            "choices": choices,
        }
    ]
    answer = prompt(questions)
    return options[choices.index(answer["menu_answer"])]


def new_note_dict(settings, note):
    print(f"It seems you don't have this {Fore.RED}note type{Fore.WHITE} set up!")
    print(
        f"Choose which fields from their card you would like to change into fields from your card"
    )

    note_dictionary = {}
    fields = settings["note_settings"]["curr_fields"][:]
    for field in note["fields"]:
        fields.insert(0, "(None)")
        questions = [
            {
                "type": "list",
                "name": "field_answer",
                "message": f"Change {field} to:",
                "choices": fields,
            }
        ]
        answer = prompt(questions)
        if answer["field_answer"] != "(None)":
            fields.remove("(None)")
        fields.remove(answer["field_answer"])
        note_dictionary[field] = answer["field_answer"]
    return note_dictionary


def ankibuddy_menu():
    questions = [
        {
            "type": "list",
            "name": "ankibuddy_menu_answer",
            "message": "What would you like to do",
            "choices": [
                "send most recent",
                "download most recent",
                "change settings",
                "exit",
            ],
        }
    ]
    answer = prompt(questions)
    return answer["ankibuddy_menu_answer"]
