import json
import requests

url = "http://127.0.0.1:8081/api/v1/chat/streaming"
body = {
  "conversation_id": "1",
  "role": "user",
  "content": "How many players in table tennis game?"
}

with requests.post(url, data=json.dumps(body), stream=True) as r:
    for chunk in r.iter_content(1024):  # or, for line in r.iter_lines():
        print(chunk)
