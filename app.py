import logging
import tempfile
from flask import Flask, request
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    MessagingApiBlob,
    TextMessage,
)
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import AudioMessageContent, MessageEvent, TextMessageContent
import speech_recognition as sr
from pydub import AudioSegment
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()
config = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))


@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print(
            "Invalid signature. Please check your channel access token/channel secret."
        )

    return "OK"


@handler.add(
    MessageEvent, message=[AudioMessageContent, TextMessageContent]
)  # 取得聲音時做的事情
def handle_message_Audio(event: MessageEvent):
    logging.info(event.message.id)
    if event.reply_token is None:
        return

    # 接收使用者語音訊息並存檔
    with ApiClient(config) as api_client:
        line_bot_blob_api = MessagingApiBlob(api_client)
        audio_content = line_bot_blob_api.get_message_content(event.message.id)

        # TODO: We might need to setup an auto-delete or sth
        with tempfile.NamedTemporaryFile(
            dir="./audio", prefix="m4a-", delete=False
        ) as tf:
            tf.write(audio_content)
            src = tf.name

    # 轉檔
    dst = f"{src}.wav"
    sound = AudioSegment.from_file(src)
    sound.export(dst, format="wav")

    # 辨識
    r = sr.Recognizer()
    with sr.AudioFile(dst) as source:
        audio = r.record(source)
    try:
        text = r.recognize_google(audio, language="zh-Hant")
    except Exception as e:
        return e.__str__

    # 回傳訊息給使用者 TODO: Load the template back, with some modification
    # with open("template/sound_reply.json", "r") as f:
    #     dt = json.load(f)
    #     dt["body"]["contents"][1]["text"] = text

    with ApiClient(config) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[
                    TextMessage(text=f"{text}")
                    # FlexSendMessage(
                    #     alt_text=f"{text}",
                    #     contents=FlexContainer.from_json(json.dumps(dt)),
                    # )
                ],
                notificationDisabled=False,
            )
        )


if __name__ == "__main__":
    app.logger.setLevel("INFO")
    app.run(host="0.0.0.0", port=8080)
