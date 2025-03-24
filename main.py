from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_API_TOKEN = os.environ['WHATSAPP_API_TOKEN']
WHATSAPP_API_URL = os.environ['WHATSAPP_API_URL']
ACCESS_TOKEN = os.environ['ACCESS_TOKEN']

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {WHATSAPP_API_TOKEN}"
}

app = Flask(__name__)
CORS(app)

@app.get("/whatsapp")
def verify_token():
    try:
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if token == ACCESS_TOKEN:
            return challenge
        else:
            return "error", 400
    except:
        return "error", 400

@app.post("/whatsapp")
def received_message():
    try:
        body = request.get_json()
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        message = value["messages"][0]
        text = message["text"]
        question_user = text["body"]
        number = message["from"]

        print("Received user message:", question_user)

        body_answer = send_message(question_user, number)
        send_status = whatsapp_service(body_answer)

        if send_status:
            print("Message sent successfully")
        else:
            print("Message sending failed")

        return "EVENT_RECEIVED"
    except Exception as e:
        print(e)
        return "EVENT_RECEIVED"

def whatsapp_service(body):
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {WHATSAPP_API_TOKEN}"
        }

        response = requests.post(WHATSAPP_API_URL, data=json.dumps(body), headers=headers)
        return response.status_code == 200
    except Exception as e:
        print(e)
        return False

def send_message(text, number):
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "text",
        "text": {
            "body": text
        }
    }
    return body

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8502, debug=True)
