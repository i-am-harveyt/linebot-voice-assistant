from ai import AI
from utils.flex_message_converter import convert_to_flex_message

import json
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
    FlexMessage,
    FlexContainer,
)
from linebot.v3.webhooks import (
    AudioMessageContent,
    MessageEvent,
    TextMessageContent,
    LocationMessageContent,
)
from pydub import AudioSegment
import requests
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
                context_chunks = self.ai.query_faiss(question)
                paragraph = "\n\n".join(context_chunks)

                # Generate response using GPT
                gpt_response = self.ai.generate_gpt_response(paragraph, question)
                logging.info(f"Generated GPT response: {gpt_response}")

                try:
                    # Parse GPT response
                    response_data = json.loads(gpt_response)
                    logging.info(f"Parsed GPT response data: {response_data}")
                    
                    # Create Flex Message based on response type
                    print(f"gpt_response: {gpt_response}")
                    print(f"response_data: {response_data}")
                    if response_data["type"] == "matched":
                        print("[handle text message] type: matched")
                        # Ensure text fields are not None or empty
                        disease_text = str(response_data.get("disease", "無法確定可能的疾病")).strip()
                        symptoms_list = response_data.get("symptoms", [])
                        symptoms_text = "、".join(symptoms_list) if symptoms_list else "無法確定相關症狀"
                        suggestions_list = response_data.get("suggestions", [])
                        suggestions_text = "、".join(suggestions_list) if suggestions_list else "建議盡快就醫"
                        
                        # Get additional info
                        additional_info = response_data.get("additional_info", {})
                        incubation_period = additional_info.get("incubation_period", "未知")
                        transmission = additional_info.get("transmission", "未知")
                        prevention_list = additional_info.get("prevention", [])
                        prevention_text = "、".join(prevention_list) if prevention_list else "未知"
                        
                        flex_message = {
                            "type": "bubble",
                            "header": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "🔍 症狀分析結果",
                                        "weight": "bold",
                                        "color": "#FFFFFF",
                                        "size": "xl"
                                    }
                                ],
                                "backgroundColor": "#27AE60",
                                "paddingAll": "20px"
                            },
                            "body": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                            {
                                                "type": "text",
                                                "text": "可能的疾病",
                                                "weight": "bold",
                                                "size": "md",
                                                "color": "#666666"
                                            },
                                            {
                                                "type": "text",
                                                "text": disease_text,
                                                "size": "md",
                                                "wrap": True,
                                                "margin": "sm",
                                                "color": "#333333"
                                            }
                                        ],
                                        "margin": "md"
                                    },
                                    {
                                        "type": "separator",
                                        "margin": "xxl"
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                            {
                                                "type": "text",
                                                "text": "相關症狀",
                                                "weight": "bold",
                                                "size": "md",
                                                "color": "#666666"
                                            },
                                            {
                                                "type": "text",
                                                "text": symptoms_text,
                                                "size": "md",
                                                "wrap": True,
                                                "margin": "sm",
                                                "color": "#333333"
                                            }
                                        ],
                                        "margin": "md"
                                    },
                                    {
                                        "type": "separator",
                                        "margin": "xxl"
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                            {
                                                "type": "text",
                                                "text": "建議事項",
                                                "weight": "bold",
                                                "size": "md",
                                                "color": "#666666"
                                            },
                                            {
                                                "type": "text",
                                                "text": suggestions_text,
                                                "size": "md",
                                                "wrap": True,
                                                "margin": "sm",
                                                "color": "#333333"
                                            }
                                        ],
                                        "margin": "md"
                                    },
                                    {
                                        "type": "separator",
                                        "margin": "xxl"
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                            {
                                                "type": "text",
                                                "text": "疾病資訊",
                                                "weight": "bold",
                                                "size": "md",
                                                "color": "#666666"
                                            },
                                            {
                                                "type": "box",
                                                "layout": "vertical",
                                                "contents": [
                                                    {
                                                        "type": "box",
                                                        "layout": "horizontal",
                                                        "contents": [
                                                            {
                                                                "type": "text",
                                                                "text": "潛伏期",
                                                                "size": "sm",
                                                                "color": "#666666",
                                                                "flex": 2
                                                            },
                                                            {
                                                                "type": "text",
                                                                "text": incubation_period,
                                                                "size": "sm",
                                                                "color": "#333333",
                                                                "flex": 3,
                                                                "wrap": True
                                                            }
                                                        ],
                                                        "margin": "sm"
                                                    },
                                                    {
                                                        "type": "box",
                                                        "layout": "horizontal",
                                                        "contents": [
                                                            {
                                                                "type": "text",
                                                                "text": "傳播方式",
                                                                "size": "sm",
                                                                "color": "#666666",
                                                                "flex": 2
                                                            },
                                                            {
                                                                "type": "text",
                                                                "text": transmission,
                                                                "size": "sm",
                                                                "color": "#333333",
                                                                "flex": 3,
                                                                "wrap": True
                                                            }
                                                        ],
                                                        "margin": "sm"
                                                    },
                                                    {
                                                        "type": "box",
                                                        "layout": "horizontal",
                                                        "contents": [
                                                            {
                                                                "type": "text",
                                                                "text": "預防措施",
                                                                "size": "sm",
                                                                "color": "#666666",
                                                                "flex": 2
                                                            },
                                                            {
                                                                "type": "text",
                                                                "text": prevention_text,
                                                                "size": "sm",
                                                                "color": "#333333",
                                                                "flex": 3,
                                                                "wrap": True
                                                            }
                                                        ],
                                                        "margin": "sm"
                                                    }
                                                ],
                                                "margin": "sm"
                                            }
                                        ],
                                        "margin": "md"
                                    }
                                ],
                                "paddingAll": "20px"
                            },
                            "footer": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "⚠️ 請注意：這只是初步分析",
                                        "color": "#FFFFFF",
                                        "align": "center",
                                        "size": "sm"
                                    }
                                ],
                                "backgroundColor": "#E74C3C",
                                "paddingAll": "15px"
                            }
                        }
                    elif response_data["type"] == "unmatched":
                        print("[handle text message] type: unmatched")
                        message_text = str(response_data.get("message", "需要更多資訊來協助您")).strip()
                        
                        if not message_text:
                            message_text = "需要更多資訊來協助您"
                        
                        flex_message = {
                            "type": "bubble",
                            "header": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "❓ 需要更多資訊",
                                        "weight": "bold",
                                        "color": "#FFFFFF",
                                        "size": "xl"
                                    }
                                ],
                                "backgroundColor": "#F39C12",
                                "paddingAll": "20px"
                            },
                            "body": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": message_text,
                                        "size": "md",
                                        "wrap": True,
                                        "color": "#333333"
                                    }
                                ],
                                "paddingAll": "20px"
                            },
                            "footer": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "請提供更多症狀描述",
                                        "color": "#FFFFFF",
                                        "align": "center",
                                        "size": "sm"
                                    }
                                ],
                                "backgroundColor": "#F39C12",
                                "paddingAll": "15px"
                            }
                        }
                    else:  # unrelated
                        print("[handle text message] type: unrelated")
                        message_text = str(response_data.get("message", "抱歉，我無法理解您的問題")).strip()
                        
                        if not message_text:
                            message_text = "抱歉，我無法理解您的問題"
                        
                        flex_message = {
                            "type": "bubble",
                            "header": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "💬 一般對話",
                                        "weight": "bold",
                                        "color": "#FFFFFF",
                                        "size": "xl"
                                    }
                                ],
                                "backgroundColor": "#3498DB",
                                "paddingAll": "20px"
                            },
                            "body": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": message_text,
                                        "size": "md",
                                        "wrap": True,
                                        "color": "#333333"
                                    }
                                ],
                                "paddingAll": "20px"
                            }
                        }

                    logging.info(f"Created Flex Message: {json.dumps(flex_message, ensure_ascii=False)}")

                    # Send Flex Message
                    with ApiClient(self.config) as api_client:
                        line_bot_api = MessagingApi(api_client)
                        response = line_bot_api.reply_message(
                            ReplyMessageRequest(
                                replyToken=event.reply_token,
                                messages=[
                                    FlexMessage(
                                        alt_text="醫療諮詢回覆",
                                        contents=FlexContainer.from_json(json.dumps(flex_message))
                                    )
                                ],
                                notificationDisabled=False,
                            )
                        )
                        logging.info(f"Line API response: {response}")

                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse GPT response as JSON: {e}")
                    # If response is not valid JSON, send as text message
                    with ApiClient(self.config) as api_client:
                        line_bot_api = MessagingApi(api_client)
                        response = line_bot_api.reply_message(
                            ReplyMessageRequest(
                                replyToken=event.reply_token,
                                messages=[TextMessage(text=gpt_response)],
                                notificationDisabled=False,
                            )
                        )

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

            try:
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
                    logging.info(f"Transcribed text: {text}")
                except Exception as e:
                    logging.error(f"Error transcribing audio: {e}")
                    raise

                # 查詢 FAISS
                context_chunks = self.ai.query_faiss(text)
                paragraph = "\n\n".join(context_chunks)

                # Generate response using GPT
                gpt_response = self.ai.generate_gpt_response(paragraph, text)
                logging.info(f"Generated GPT response: {gpt_response}")

                try:
                    # Parse GPT response
                    response_data = json.loads(gpt_response)
                    
                    # Create Flex Message based on response type
                    if response_data["type"] == "matched":
                        print("[handle audio message] type: matched")
                        # Ensure text fields are not None or empty
                        disease_text = str(response_data.get("disease", "無法確定可能的疾病")).strip()
                        symptoms_list = response_data.get("symptoms", [])
                        symptoms_text = "、".join(str(s) for s in symptoms_list) if symptoms_list else "無法確定相關症狀"
                        suggestions_list = response_data.get("suggestions", [])
                        suggestions_text = "、".join(str(s) for s in suggestions_list) if suggestions_list else "建議盡快就醫"
                        
                        # Get additional info
                        additional_info = response_data.get("additional_info", {})
                        incubation_period = str(additional_info.get("incubation_period", "未知")).strip()
                        transmission = str(additional_info.get("transmission", "未知")).strip()
                        prevention_list = additional_info.get("prevention", [])
                        prevention_text = "、".join(str(p) for p in prevention_list) if prevention_list else "未知"
                        
                        flex_message = {
                            "type": "bubble",
                            "header": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "🔍 症狀分析結果",
                                        "weight": "bold",
                                        "color": "#FFFFFF",
                                        "size": "xl"
                                    }
                                ],
                                "backgroundColor": "#27AE60",
                                "paddingAll": "20px"
                            },
                            "body": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                            {
                                                "type": "text",
                                                "text": "可能的疾病",
                                                "weight": "bold",
                                                "size": "md",
                                                "color": "#666666"
                                            },
                                            {
                                                "type": "text",
                                                "text": disease_text,
                                                "size": "md",
                                                "wrap": True,
                                                "margin": "sm",
                                                "color": "#333333"
                                            }
                                        ],
                                        "margin": "md"
                                    },
                                    {
                                        "type": "separator",
                                        "margin": "xxl"
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                            {
                                                "type": "text",
                                                "text": "相關症狀",
                                                "weight": "bold",
                                                "size": "md",
                                                "color": "#666666"
                                            },
                                            {
                                                "type": "text",
                                                "text": symptoms_text,
                                                "size": "md",
                                                "wrap": True,
                                                "margin": "sm",
                                                "color": "#333333"
                                            }
                                        ],
                                        "margin": "md"
                                    },
                                    {
                                        "type": "separator",
                                        "margin": "xxl"
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                            {
                                                "type": "text",
                                                "text": "建議事項",
                                                "weight": "bold",
                                                "size": "md",
                                                "color": "#666666"
                                            },
                                            {
                                                "type": "text",
                                                "text": suggestions_text,
                                                "size": "md",
                                                "wrap": True,
                                                "margin": "sm",
                                                "color": "#333333"
                                            }
                                        ],
                                        "margin": "md"
                                    },
                                    {
                                        "type": "separator",
                                        "margin": "xxl"
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                            {
                                                "type": "text",
                                                "text": "疾病資訊",
                                                "weight": "bold",
                                                "size": "md",
                                                "color": "#666666"
                                            },
                                            {
                                                "type": "box",
                                                "layout": "vertical",
                                                "contents": [
                                                    {
                                                        "type": "box",
                                                        "layout": "horizontal",
                                                        "contents": [
                                                            {
                                                                "type": "text",
                                                                "text": "潛伏期",
                                                                "size": "sm",
                                                                "color": "#666666",
                                                                "flex": 2
                                                            },
                                                            {
                                                                "type": "text",
                                                                "text": incubation_period,
                                                                "size": "sm",
                                                                "color": "#333333",
                                                                "flex": 3,
                                                                "wrap": True
                                                            }
                                                        ],
                                                        "margin": "sm"
                                                    },
                                                    {
                                                        "type": "box",
                                                        "layout": "horizontal",
                                                        "contents": [
                                                            {
                                                                "type": "text",
                                                                "text": "傳播方式",
                                                                "size": "sm",
                                                                "color": "#666666",
                                                                "flex": 2
                                                            },
                                                            {
                                                                "type": "text",
                                                                "text": transmission,
                                                                "size": "sm",
                                                                "color": "#333333",
                                                                "flex": 3,
                                                                "wrap": True
                                                            }
                                                        ],
                                                        "margin": "sm"
                                                    },
                                                    {
                                                        "type": "box",
                                                        "layout": "horizontal",
                                                        "contents": [
                                                            {
                                                                "type": "text",
                                                                "text": "預防措施",
                                                                "size": "sm",
                                                                "color": "#666666",
                                                                "flex": 2
                                                            },
                                                            {
                                                                "type": "text",
                                                                "text": prevention_text,
                                                                "size": "sm",
                                                                "color": "#333333",
                                                                "flex": 3,
                                                                "wrap": True
                                                            }
                                                        ],
                                                        "margin": "sm"
                                                    }
                                                ],
                                                "margin": "sm"
                                            }
                                        ],
                                        "margin": "md"
                                    }
                                ],
                                "paddingAll": "20px"
                            },
                            "footer": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "⚠️ 請注意：這只是初步分析",
                                        "color": "#FFFFFF",
                                        "align": "center",
                                        "size": "sm"
                                    }
                                ],
                                "backgroundColor": "#E74C3C",
                                "paddingAll": "15px"
                            }
                        }
                    elif response_data["type"] == "unmatched":
                        print("[handle audio message] type: unmatched")
                        message_text = str(response_data.get("message", "需要更多資訊來協助您")).strip()
                        
                        if not message_text:
                            message_text = "需要更多資訊來協助您"
                        
                        flex_message = {
                            "type": "bubble",
                            "header": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "❓ 需要更多資訊",
                                        "weight": "bold",
                                        "color": "#FFFFFF",
                                        "size": "xl"
                                    }
                                ],
                                "backgroundColor": "#F39C12",
                                "paddingAll": "20px"
                            },
                            "body": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": message_text,
                                        "size": "md",
                                        "wrap": True,
                                        "color": "#333333"
                                    }
                                ],
                                "paddingAll": "20px"
                            },
                            "footer": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "請提供更多症狀描述",
                                        "color": "#FFFFFF",
                                        "align": "center",
                                        "size": "sm"
                                    }
                                ],
                                "backgroundColor": "#F39C12",
                                "paddingAll": "15px"
                            }
                        }
                    else:  # unrelated
                        print("[handle audio message] type: unrelated")
                        message_text = str(response_data.get("message", "抱歉，我無法理解您的問題")).strip()
                        
                        if not message_text:
                            message_text = "抱歉，我無法理解您的問題"
                        
                        flex_message = {
                            "type": "bubble",
                            "header": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "💬 一般對話",
                                        "weight": "bold",
                                        "color": "#FFFFFF",
                                        "size": "xl"
                                    }
                                ],
                                "backgroundColor": "#3498DB",
                                "paddingAll": "20px"
                            },
                            "body": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": message_text,
                                        "size": "md",
                                        "wrap": True,
                                        "color": "#333333"
                                    }
                                ],
                                "paddingAll": "20px"
                            }
                        }

                    logging.info(f"Created Flex Message: {json.dumps(flex_message, ensure_ascii=False)}")

                    # Send Flex Message
                    with ApiClient(self.config) as api_client:
                        line_bot_api = MessagingApi(api_client)
                        response = line_bot_api.reply_message(
                            ReplyMessageRequest(
                                replyToken=event.reply_token,
                                messages=[
                                    FlexMessage(
                                        alt_text="醫療諮詢回覆",
                                        contents=FlexContainer.from_json(json.dumps(flex_message))
                                    )
                                ],
                                notificationDisabled=False,
                            )
                        )
                        logging.info(f"Line API response: {response}")

                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse GPT response as JSON: {e}")
                    # If response is not valid JSON, send as text message
                    with ApiClient(self.config) as api_client:
                        line_bot_api = MessagingApi(api_client)
                        response = line_bot_api.reply_message(
                            ReplyMessageRequest(
                                replyToken=event.reply_token,
                                messages=[TextMessage(text=gpt_response)],
                                notificationDisabled=False,
                            )
                        )

            except Exception as e:
                error_message = f"Error processing audio message: {str(e)}"
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
                                        text="抱歉，處理您的語音訊息時發生錯誤。請稍後再試。"
                                    )
                                ],
                                notificationDisabled=False,
                            )
                        )
                        logging.info("Successfully sent error message to user")
                except Exception as reply_error:
                    logging.error(f"Failed to send error message: {str(reply_error)}")

                return error_message

        @self.handler.add(MessageEvent, message=LocationMessageContent)
        def handle_location_message(event: MessageEvent):
            def search_nearby_clinics(lat, lng, radius=2000, keyword="診所"):
                url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
                params = {
                    "location": f"{lat},{lng}",
                    "radius": radius,
                    "keyword": keyword,
                    "type": "doctor",
                    "language": "zh-TW",
                    "key": os.getenv("GOOGLE_MAPS_API_KEY"),
                }

                response = requests.get(url, params=params)
                data = response.json()

                if data.get("status") != "OK":
                    logging.warning(f"Google Places API error: {data.get('status')}")
                    return []

                results = []
                for place in data.get("results", [])[:5]:  # 只取前 5 筆
                    results.append(
                        {
                            "name": place.get("name"),
                            "address": place.get("vicinity"),
                            "lat": place["geometry"]["location"]["lat"],
                            "lng": place["geometry"]["location"]["lng"],
                        }
                    )

                return results

            def create_clinic_bubbles(clinics):
                bubbles = []
                for clinic in clinics:
                    map_link = f"https://maps.google.com/?q={clinic['lat']},{clinic['lng']}"
                    bubble = {
                        "type": "bubble",
                        "size": "mega",
                        "header": {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "🏥",
                                            "size": "xl"
                                        },
                                        {
                                            "type": "text",
                                            "text": clinic["name"],
                                            "weight": "bold",
                                            "color": "#FFFFFF",
                                            "size": "xl",
                                            "wrap": True,
                                            "margin": "md"
                                        }
                                    ],
                                    "alignItems": "center"
                                }
                            ],
                            "backgroundColor": "#27AE60",
                            "paddingAll": "20px"
                        },
                        "body": {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                        {
                                            "type": "box",
                                            "layout": "horizontal",
                                            "contents": [
                                                {
                                                    "type": "text",
                                                    "text": "📍",
                                                    "size": "sm",
                                                    "flex": 0
                                                },
                                                {
                                                    "type": "text",
                                                    "text": "地址",
                                                    "weight": "bold",
                                                    "size": "sm",
                                                    "color": "#AAAAAA",
                                                    "flex": 0,
                                                    "margin": "md"
                                                }
                                            ],
                                            "alignItems": "center"
                                        },
                                        {
                                            "type": "text",
                                            "text": clinic["address"],
                                            "size": "md",
                                            "wrap": True,
                                            "margin": "sm",
                                            "color": "#666666"
                                        }
                                    ],
                                    "spacing": "sm",
                                    "paddingAll": "13px"
                                },
                                {
                                    "type": "separator",
                                    "margin": "xxl"
                                },
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "點擊下方按鈕查看地圖位置",
                                            "color": "#AAAAAA",
                                            "size": "sm",
                                            "align": "center"
                                        }
                                    ],
                                    "margin": "xxl"
                                }
                            ],
                            "paddingAll": "20px"
                        },
                        "footer": {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "button",
                                    "style": "primary",
                                    "action": {
                                        "type": "uri",
                                        "label": "🗺️ 查看地圖",
                                        "uri": map_link
                                    },
                                    "height": "sm",
                                    "color": "#2ECC71"
                                }
                            ],
                            "backgroundColor": "#F5F5F5",
                            "paddingAll": "15px"
                        },
                        "styles": {
                            "header": {
                                "separator": False
                            },
                            "footer": {
                                "separator": False
                            }
                        }
                    }
                    bubbles.append(bubble)
                return bubbles

            latitude, longitude = event.message.latitude, event.message.longitude
            logging.info(f"Received: {latitude}, {longitude}")

            try:
                clinics = search_nearby_clinics(latitude, longitude)

                if not clinics:
                    reply = "找不到附近的診所，建議您聯繫 1922 或前往大型醫院急診。"
                    with ApiClient(self.config) as api_client:
                        line_bot_api = MessagingApi(api_client)
                        line_bot_api.reply_message(
                            ReplyMessageRequest(
                                replyToken=event.reply_token,
                                messages=[TextMessage(text=reply)],
                                notificationDisabled=False,
                            )
                        )
                else:
                    # Load template
                    with open("template/clinic_reply.json", "r") as f:
                        template = json.load(f)
                    
                    # Create clinic bubbles
                    clinic_bubbles = create_clinic_bubbles(clinics)
                    template["contents"] = clinic_bubbles

                    # Send Flex Message
                    with ApiClient(self.config) as api_client:
                        line_bot_api = MessagingApi(api_client)
                        line_bot_api.reply_message(
                            ReplyMessageRequest(
                                replyToken=event.reply_token,
                                messages=[
                                    FlexMessage(
                                        alt_text="附近診所資訊",
                                        contents=FlexContainer.from_json(json.dumps(template))
                                    )
                                ],
                                notificationDisabled=False,
                            )
                        )

            except Exception as e:
                logging.error(f"Error during clinic search: {e}")
                with ApiClient(self.config) as api_client:
                    line_bot_api = MessagingApi(api_client)
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            replyToken=event.reply_token,
                            messages=[
                                TextMessage(text="目前無法查詢附近診所，請稍後再試。")
                            ],
                            notificationDisabled=False,
                        )
                    )

        @self.app.route("/test-gpt", methods=["POST"])
        def test_gpt():
            """Test GPT response endpoint"""
            try:
                data = request.get_json()
                if not data or "paragraph" not in data or "question" not in data:
                    return {"error": "Please provide paragraph and question"}, 400

                paragraph = data["paragraph"]
                question = data["question"]

                # Generate response using GPT
                response = self.ai.generate_gpt_response(paragraph, question)

                return {"status": "success", "response": response}
            except Exception as e:
                logging.error(f"Error in GPT test: {e}")
                return {"error": str(e)}, 500

    def run(self):
        self.app.logger.setLevel("INFO")
        self.app.run(host="0.0.0.0", port=8080)
