from flask import request, jsonify
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    MessagingApiBlob,
    TextMessage,
    FlexMessage,
)
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import AudioMessageContent, MessageEvent, TextMessageContent
import speech_recognition as sr
from pydub import AudioSegment
import tempfile
import logging
import os
import json
from openai import OpenAI
from prompts.medical_advisor import MEDICAL_ADVISOR_SYSTEM_PROMPT, format_medical_question

def load_template(template_name):
    """Load template from file"""
    template_path = os.path.join("template", template_name)
    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)

def init_routes(app, config, handler, client):
    @app.route("/webhook", methods=["POST"])
    def webhook():
        signature = request.headers.get("X-Line-Signature", "")
        body = request.get_data(as_text=True)
        logging.info("Received webhook request")
        logging.info(f"Signature: {signature}")
        logging.debug(f"Request body: {body}")

        try:
            handler.handle(body, signature)
            logging.info("Successfully handled webhook request")
        except InvalidSignatureError:
            logging.error("Invalid signature. Please check your channel access token/channel secret.")
            return jsonify({"error": "Invalid signature"}), 400
        except Exception as e:
            logging.error(f"Error handling webhook: {str(e)}")
            return jsonify({"error": str(e)}), 500

        return "OK"

    @handler.add(MessageEvent, message=TextMessageContent)
    def handle_text_message(event):
        """Handle text messages"""
        logging.info(f"Received text message: {event.message.text}")
        logging.info(f"Reply token: {event.reply_token}")
        
        if event.reply_token is None:
            logging.warning("Reply token is None, skipping message")
            return

        try:
            # Test data
            test_paragraph = """
            糖尿病是一種慢性代謝性疾病，主要特徵是血糖水平持續升高。
            常見症狀包括：多飲、多尿、多食、體重下降。
            治療方式包括：飲食控制、規律運動、口服藥物或胰島素注射。
            定期監測血糖和定期就醫檢查非常重要。
            """
            test_question = event.message.text
            logging.info(f"Processing question: {test_question}")

            # Generate response using GPT
            gpt_response = generate_gpt_response(test_paragraph, test_question)
            logging.info(f"Generated GPT response: {gpt_response}")

            # Send simple text response
            with ApiClient(config) as api_client:
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
                    logging.error(f"Error sending message to Line API: {str(api_error)}")
                    raise
                
        except Exception as e:
            error_message = f"Error processing message: {str(e)}"
            logging.error(error_message)
            
            # Try to send error message to user
            try:
                with ApiClient(config) as api_client:
                    line_bot_api = MessagingApi(api_client)
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            replyToken=event.reply_token,
                            messages=[TextMessage(text="抱歉，處理您的訊息時發生錯誤。請稍後再試。")],
                            notificationDisabled=False,
                        )
                    )
                    logging.info("Successfully sent error message to user")
            except Exception as reply_error:
                logging.error(f"Failed to send error message: {str(reply_error)}")
            
            return error_message
        
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

    @app.route("/test-gpt", methods=["POST"])
    def test_gpt():
        """Test GPT response endpoint"""
        try:
            data = request.get_json()
            if not data or 'paragraph' not in data or 'question' not in data:
                return {"error": "Please provide paragraph and question"}, 400

            paragraph = data['paragraph']
            question = data['question']

            # Generate response using GPT
            response = generate_gpt_response(paragraph, question)
            
            return {
                "status": "success",
                "response": response
            }
        except Exception as e:
            logging.error(f"Error in GPT test: {e}")
            return {"error": str(e)}, 500 

    def generate_gpt_response(paragraph: str, question: str) -> str:
        """Generate response using GPT"""
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": MEDICAL_ADVISOR_SYSTEM_PROMPT},
                    {"role": "user", "content": format_medical_question(paragraph, question)}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error generating GPT response: {e}")
            return "抱歉，我現在無法回答這個問題。" 