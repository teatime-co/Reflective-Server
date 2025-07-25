import json
import requests
import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
jsonl_path = os.path.join(script_dir, 'journal_entries_with_tags.jsonl')

with open(jsonl_path, 'r') as f:
    for line in f:
        entry = json.loads(line)
        # print(entry)
        response = requests.post("http://127.0.0.1:8000/api/logs/", json=entry)
        print(response.status_code)