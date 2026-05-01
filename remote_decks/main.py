from aqt import mw
from aqt.utils import showInfo, qconnect
from aqt.qt import QAction, QMenu, QInputDialog, QLineEdit, QKeySequence

try:
    echo_mode_normal = QLineEdit.EchoMode.Normal
except AttributeError:
    echo_mode_normal = QLineEdit.Normal

import sys
import csv
import urllib.request

from .parseRemoteDeck import getRemoteDeck

def syncDecks():
    col = mw.col
    config = mw.addonManager.getConfig(__name__)
    if not config:
        config = {"remote-decks": {}}

    for deckKey in config["remote-decks"].keys():
        try:
            currentRemoteInfo = config["remote-decks"][deckKey]
            deckName = currentRemoteInfo["deckName"]
            remoteDeck = getRemoteDeck(currentRemoteInfo["url"])
            remoteDeck.deckName = deckName
            deck_id = get_or_create_deck(col, deckName)
            create_or_update_notes(col, remoteDeck, deck_id)
        except Exception as e:
            deckMessage = f"\nThe following deck failed to sync: {deckName}"
            showInfo(str(e) + deckMessage)
            raise

    showInfo("Synchronization complete")

def get_or_create_deck(col, deckName):
    deck = col.decks.by_name(deckName)
    if deck is None:
        deck_id = col.decks.id(deckName)
    else:
        deck_id = deck["id"]
    return deck_id

def create_or_update_notes(col, remoteDeck, deck_id):
    # Dictionaries for existing notes
    existing_notes = {}
    existing_note_ids = {}

    # Fetch existing notes in the deck
    for nid in col.find_notes(f'deck:"{remoteDeck.deckName}"'):
        note = col.get_note(nid)
        anki_id = note.get('AnkiID', '')
        if not anki_id:
            continue
            
        existing_notes[anki_id] = note
        existing_note_ids[anki_id] = nid

    # Set to keep track of keys from Google Sheets
    gs_ids = set()

    for question in remoteDeck.questions:
        card_type = question['type']
        fields = question['fields']
        tags = question.get('tags', [])
        note_id = fields.get('AnkiID', '')
        if not note_id:
            showInfo(f"Skipping card without AnkiID: {fields.get('Front', 'Unknown')}")
            continue
            
        gs_ids.add(note_id)

        if note_id in existing_notes:
            note = existing_notes[note_id] # will update existing note
        
            if card_type == 'Cloze':
                note["Text"] = fields.get('Text', '')
                note["Extra"] = fields.get('Extra', '')
            elif card_type == 'Basic':
                note["Front"] = fields.get('Front', '')
                note["Back"] = fields.get('Back', '')
            else:
                continue

            note.tags = tags
            note.flush()

        else:
            # creating new note
            model_name = "Cloze" if card_type == 'Cloze' else "Basic"
            model = col.models.by_name(model_name)

            if model is None:
                showInfo(f"the '{model_name}' doesnt exist, pls create")
                continue

            col.models.set_current(model)
            model['did'] = deck_id
            col.models.save(model)

            note = col.new_note(model)

            if card_type == 'Cloze':
                note['Text'] = fields.get('Text', '')
                note['Extra'] = fields.get('Extra', '')
            elif card_type == 'Basic':
                note['Front'] = fields.get('Front', '')
                note['Back'] = fields.get('Back', '')
                
            note["AnkiID"] = note_id 
            note.tags = tags
            col.add_note(note, deck_id)
  
    # Find notes that are in Anki but not in Google Sheets
    anki_ids = set(existing_notes.keys())
    notes_to_delete = anki_ids - gs_ids

    # Remove the corresponding notes
    if notes_to_delete:
        note_ids_to_delete = [existing_note_ids[key] for key in notes_to_delete]
        col.remove_notes(note_ids_to_delete)

    # Save changes
    col.save()

def addNewDeck():
    url, okPressed = QInputDialog.getText(
        mw, "Add New Remote Deck", "URL of published CSV:", echo_mode_normal, ""
    )
    if not okPressed or not url.strip():
        return

    url = url.strip()

    deckName, okPressed = QInputDialog.getText(
        mw, "Deck Name", "Enter the name of the deck:", echo_mode_normal, ""
    )
    if not okPressed or not deckName.strip():
        deckName = "Deck from CSV"

    if "output=csv" not in url:
        showInfo("The provided URL does not appear to be a published CSV from Google Sheets.")
        return

    config = mw.addonManager.getConfig(__name__)
    if not config:
        config = {"remote-decks": {}}

    if url in config["remote-decks"]:
        showInfo(f"The deck has already been added before: {url}")
        return

    try:
        deck = getRemoteDeck(url)
        deck.deckName = deckName
    except Exception as e:
        showInfo(f"Error fetching the remote deck:\n{e}")
        return

    config["remote-decks"][url] = {"url": url, "deckName": deckName}
    mw.addonManager.writeConfig(__name__, config)
    syncDecks()

def removeRemoteDeck():
    # Get the add-on configuration
    config = mw.addonManager.getConfig(__name__)
    if not config:
        config = {"remote-decks": {}}

    remoteDecks = config["remote-decks"]

    # Get all deck names
    deckNames = [remoteDecks[key]["deckName"] for key in remoteDecks]

    if len(deckNames) == 0:
        showInfo("There are currently no remote decks.")
        return

    # Ask the user to select a deck
    selection, okPressed = QInputDialog.getItem(
        mw,
        "Select a Deck to Unlink",
        "Select a deck to unlink:",
        deckNames,
        0,
        False
    )

    # Remove the deck
    if okPressed:
        for key in list(remoteDecks.keys()):
            if selection == remoteDecks[key]["deckName"]:
                del remoteDecks[key]
                break

        # Save the updated configuration
        mw.addonManager.writeConfig(__name__, config)
        showInfo(f"The deck '{selection}' has been unlinked.")
