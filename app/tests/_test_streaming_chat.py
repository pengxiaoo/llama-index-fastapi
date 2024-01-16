import json
import requests

url = "http://127.0.0.1:8081/api/v1/chat/streaming_dialog"
body = {
  "conversation_id": "1",
  "role": "user",
  "dialog": "How many players in table tennis game?",
  "sequence_num": 0
}

with requests.post(url, data=json.dumps(body), stream=True) as r:
    for chunk in r.iter_content(1024):  # or, for line in r.iter_lines():
        print(chunk)
