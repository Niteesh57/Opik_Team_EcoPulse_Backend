

import requests
import time

REQUEST_ID = "feb0ea43-653f-4bb9-9462-5c73c44769db"
TOKEN = "3136|q4GYfQQKAt1C6jaeiyPqHL0wu4EXzfUZcfjZwuHn8138bff8"

status_url = f"https://api.deapi.ai/api/v1/client/request-status/{REQUEST_ID}"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json"
}

response = requests.get(status_url, headers=headers)
data = response.json()

status = data
print(status)