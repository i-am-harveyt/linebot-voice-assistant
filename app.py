from flask import Flask, request
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError,
)
from linebot.models import (
    MessageEvent,FlexSendMessage,AudioMessage,
)
import json
import speech_recognition as sr
from pydub import AudioSegment
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv() 
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

@app.route('/webhook', methods=['POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")

    return 'OK'

@handler.add(MessageEvent, message = AudioMessage)  # 取得聲音時做的事情
def handle_message_Audio(event):
    #接收使用者語音訊息並存檔
    UserID = event.source.user_id
    path="./audio/"+UserID+".mp3"
    audio_content = line_bot_api.get_message_content(event.message.id)
    with open(path, 'wb') as fd:
        for chunk in audio_content.iter_content():
            fd.write(chunk)        
    fd.close()
    
    #轉檔
    dst=path.replace("mp3","wav")
    sound = AudioSegment.from_file(path)
    sound.export(dst, format="wav")
    
    #辨識
    r = sr.Recognizer()
    with sr.AudioFile(dst) as source:
        audio = r.record(source)
    try:
        text = r.recognize_google(audio,language='zh-Hant')
    except Exception as e:
        return "None"
    print(text)

    #回傳訊息給使用者
    with open(f'template/sound_reply.json', 'r') as f:
            dt = json.load(f)
    dt['body']['contents'][1]['text'] = text
    print(dt)
    
    line_bot_api.reply_message(
        event.reply_token, FlexSendMessage(alt_text=f"{text}", contents=dt))

if __name__ == '__main__':
    app.run(port=5002)
