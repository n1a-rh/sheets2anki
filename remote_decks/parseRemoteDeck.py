import csv
import requests
import re  # Import the 're' module for regular expressions

class RemoteDeck:
    def __init__(self):
        self.deckName = ""
        self.questions = []  # Keep using 'questions' attribute
        self.media = []

    def getMedia(self):
        return self.media

def getRemoteDeck(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        csv_data = response.content.decode('utf-8')
    except Exception as e:
        raise Exception(f"Error downloading or reading the CSV: {e}")

    data = parse_csv_data(csv_data)
    remoteDeck = build_remote_deck_from_csv(data)
    return remoteDeck

def parse_csv_data(csv_data):
    reader = csv.reader(csv_data.splitlines())
    data = list(reader)
    return data

def build_remote_deck_from_csv(data):
    # Process headers to find indices of 'question', 'answer', and 'tags'
    headers = [h.strip().lower() for h in data[0]]
    print("Headers:", headers)  # Debug message

    id_index = headers.index('id') if 'id' in headers else None 

    question_index = headers.index('question') if 'question' in headers else headers.index('front') if 'front' in headers else 0
    answer_index = headers.index('answer') if 'answer' in headers else headers.index('back') if 'back' in headers else 1
    tag_index = headers.index('tags') if 'tags' in headers else None

    print("Indices - Question:", question_index, "Answer:", answer_index, "Tags:", tag_index)  # Debug message

    questions = []
    for row_num, row in enumerate(data[1:], start=2):  # Start at line 2 (after headers)
        print(f"Processing row {row_num}: {row}")  # Debug message

        # Skip empty rows
        if not any(cell.strip() for cell in row):
            print(f"Row {row_num} skipped because it is empty")
            continue

        anki_id = '' 
        if id_index is not None:
            anki_id = row[id_index].strip()
        if not anki_id:
            print(f"row {row_num} skipped: missing id")
            continue

        # Get question and answer
        try:
            question_text = row[question_index].strip()
            answer_text = row[answer_index].strip()
        except IndexError:
            print(f"Row {row_num} skipped due to missing question or answer")
            continue

        # Get tags if available
        tag_text = ''
        if tag_index is not None and tag_index < len(row):
            tag_text = row[tag_index].strip()
        tags = tag_text.split('::') if tag_text else []
        tags = [tag.strip() for tag in tags if tag.strip()]

        # Detect if it's a Cloze deletion
        if re.search(r'{{c\d+::.*?}}', question_text):
            card_type = 'Cloze'
            fields = {
                'AnkiID': anki_id,
                'Text': question_text,
                'Extra': answer_text  # The 'Extra' field can be empty
            }
        else:
            card_type = 'Basic'
            fields = {
                'AnkiID': anki_id,
                'Front': question_text,
                'Back': answer_text
            }

        print(f"Detected card type: {card_type}")  # Debug message

        # Create question dictionary
        question = {
            'type': card_type,
            'fields': fields,
            'tags': tags
        }
        questions.append(question)
        print(f"Added question: {question_text}")  # Debug message

    remoteDeck = RemoteDeck()
    remoteDeck.deckName = "Deck from CSV"
    remoteDeck.questions = questions  # Keep using 'questions' attribute

    print(f"Total questions added: {len(questions)}")  # Debug message

    return remoteDeck
