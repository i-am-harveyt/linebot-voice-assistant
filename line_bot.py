from ai import AI

import logging
import os
import tempfile

from flask import Flask, request, jsonify
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    MessagingApiBlob,
    TextMessage,
)
from linebot.v3.webhooks import AudioMessageContent, MessageEvent, TextMessageContent
from pydub import AudioSegment
import speech_recognition as sr


class Bot:
    def __init__(self):
        self.app: Flask = Flask(__name__)
        self.config = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
        self.handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
        self.__init_routes()

        self.ai = AI()

    def __init_routes(self):
        @self.app.route("/webhook", methods=["POST"])
        def webhook():
            signature = request.headers.get("X-Line-Signature", "")
            body = request.get_data(as_text=True)
            logging.info("Received webhook request")
            logging.info(f"Signature: {signature}")
            logging.debug(f"Request body: {body}")

            try:
                self.handler.handle(body, signature)
                logging.info("Successfully handled webhook request")
            except InvalidSignatureError:
                logging.error(
                    "Invalid signature. Please check your channel access token/channel secret."
                )
                return jsonify({"error": "Invalid signature"}), 400
            except Exception as e:
                logging.error(f"Error handling webhook: {str(e)}")
                return jsonify({"error": str(e)}), 500

            return "OK"

        @self.handler.add(MessageEvent, message=TextMessageContent)
        def handle_text_message(event: MessageEvent):
            """Handle text messages"""

            question = event.message.to_str()
            logging.info(f"Received text message: {question}")

            if event.reply_token is None:
                logging.warning("Reply token is None, skipping message")
                return

            try:
                # 查詢 FAISS
                context_chunks = self.ai.query_faiss(question)  # ← 取得向量最相近片段
                paragraph = "\n\n".join(context_chunks)

                context_chunks = self.ai.query_faiss(question)
                logging.info(f"Retrieved {len(context_chunks)} chunks")

                # Generate response using GPT
                gpt_response = self.ai.generate_gpt_response(paragraph, question)
                logging.info(f"Generated GPT response: {gpt_response}")

                # Send simple text response
                with ApiClient(self.config) as api_client:
                    line_bot_api = MessagingApi(api_client)
                    try:
                        response = line_bot_api.reply_message(
                            ReplyMessageRequest(
                                replyToken=event.reply_token,
                                messages=[TextMessage(text=gpt_response)],
                                notificationDisabled=False,
                            )
                        )
                        logging.info(f"Line API response: {response}")
                    except Exception as api_error:
                        logging.error(
                            f"Error sending message to Line API: {str(api_error)}"
                        )
                        raise

            except Exception as e:
                error_message = f"Error processing message: {str(e)}"
                logging.error(error_message)

                # Try to send error message to user
                try:
                    with ApiClient(self.config) as api_client:
                        line_bot_api = MessagingApi(api_client)
                        line_bot_api.reply_message(
                            ReplyMessageRequest(
                                replyToken=event.reply_token,
                                messages=[
                                    TextMessage(
                                        text="抱歉，處理您的訊息時發生錯誤。請稍後再試。"
                                    )
                                ],
                                notificationDisabled=False,
                            )
                        )
                        logging.info("Successfully sent error message to user")
                except Exception as reply_error:
                    logging.error(f"Failed to send error message: {str(reply_error)}")

                return error_message

        @self.handler.add(MessageEvent, message=AudioMessageContent)
        def handle_audio_message(event: MessageEvent):
            logging.info(event.message.id)
            if event.reply_token is None:
                return

            # 接收使用者語音訊息並存檔
            with ApiClient(self.config) as api_client:
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

            with ApiClient(self.config) as api_client:
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

        @self.app.route("/test-gpt", methods=["POST"])
        def test_gpt():
            """Test GPT response endpoint"""
            try:
                data = request.get_json()
                if not data or 'paragraph' not in data or 'question' not in data:
                    return {"error": "Please provide paragraph and question"}, 400

                paragraph = data['paragraph']
                question = data['question']

                # Generate response using GPT
                response = self.ai.generate_gpt_response(paragraph, question)
                
                return {
                    "status": "success",
                    "response": response
                }
            except Exception as e:
                logging.error(f"Error in GPT test: {e}")
                return {"error": str(e)}, 500 

    def run(self):
        self.app.logger.setLevel("INFO")
        self.app.run(host="0.0.0.0", port=8080)
