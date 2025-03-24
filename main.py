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

@app.get("/greet")
def greet():
    return "Hello, world!"

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)