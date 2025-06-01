import logging
from flask import Flask
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration
import os
from dotenv import load_dotenv
from openai import OpenAI
from routes import init_routes

app = Flask(__name__)
load_dotenv()
config = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
init_routes(app, config, handler, client)

if __name__ == "__main__":
    app.logger.setLevel("INFO")
    app.run(host="0.0.0.0", port=8080)
