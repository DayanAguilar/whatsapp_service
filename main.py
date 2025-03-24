from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_API_TOKEN = os.environ['WHATSAPP_API_TOKEN']
WHATSAPP_API_URL = os.environ['WHATSAPP_API_URL']