# LineBot Voice Assistant

## Description

## Installation

### Developement

If you want to run this on your own machine, please make sure:

1. [ffmpeg](https://ffmpeg.org/): to handle the audio file.
2. [uv](https://docs.astral.sh/uv/): modern python package manager
3. [ngrok](https://ngrok.com/): to expose your local endpoint for LINE Bot Webhook URL

are insalled on your computer.

### Project Setup

#### Install dependencies:

```shell
uv pip install -r requirements.txt
```

#### Environment Setup

You can get your

1. channel-id from LINE Developers Console > Basic Settings > Channel ID
2. channel-secret from LINE Developers Console > Channel Secret

Get your line channel access token with:

```shell
curl -v -X POST https://api.line.me/oauth2/v3/token \
-H 'Content-Type: application/x-www-form-urlencoded' \
--data-urlencode 'grant_type=client_credentials' \
--data-urlencode 'client_id=<channel-id>' \
--data-urlencode 'client_secret=<channel-secret>'
```

Create a `.env` file, fill in the secrets:

```
LINE_CHANNEL_ACCESS_TOKEN=<your-token>
LINE_CHANNEL_SECRET=<your-secret>
OPENAI_API_KEY=<your-openai-api-key>
GOOGLE_MAPS_API_KEY=<your-google-map-api-key>
```

Run the program on local machine for testing:

```shell
uv run app.py
```

The program will run on port 8080.

Expose your endpoint with ngrok:

```bash
ngrok http http://127.0.0.1:8080
```

You'll see a dashboard, paste the URL following the "Forwarding" to LINE Developer Console > Messaging API > Webhook settings > Webhook URL.

Add `/webhook` at the end of the Webhook URL.

## Testing

### Test GPT Response

You can test the GPT response using the `/test-gpt` endpoint. Here are some example test cases:

1. Test with matching symptoms:
```bash
curl -X POST http://localhost:8080/test-gpt \
-H "Content-Type: application/json" \
-d '{
    "paragraph": "糖尿病是一種慢性代謝性疾病，主要特徵是血糖水平持續升高。常見症狀包括：多飲、多尿、多食、體重下降。治療方式包括：飲食控制、規律運動、口服藥物或胰島素注射。",
    "question": "我最近常常口渴，喝很多水，也常常上廁所，體重也下降了。"
}'
```

2. Test with non-matching symptoms:
```bash
curl -X POST http://localhost:8080/test-gpt \
-H "Content-Type: application/json" \
-d '{
    "paragraph": "糖尿病是一種慢性代謝性疾病，主要特徵是血糖水平持續升高。常見症狀包括：多飲、多尿、多食、體重下降。治療方式包括：飲食控制、規律運動、口服藥物或胰島素注射。",
    "question": "我最近頭痛，而且會發燒到39度。"
}'
```

3. Test with unrelated question:
```bash
curl -X POST http://localhost:8080/test-gpt \
-H "Content-Type: application/json" \
-d '{
    "paragraph": "糖尿病是一種慢性代謝性疾病，主要特徵是血糖水平持續升高。常見症狀包括：多飲、多尿、多食、體重下降。治療方式包括：飲食控制、規律運動、口服藥物或胰島素注射。",
    "question": "今天天氣如何？"
}'
```

Expected responses:

1. For matching symptoms:
```json
{
    "status": "success",
    "response": {
        "type": "matched",
        "title": "症狀相符",
        "disease": "糖尿病",
        "symptoms": [
            "多飲",
            "多尿",
            "體重下降"
        ],
        "suggestions": [
            "盡快就醫進行血糖檢查",
            "控制飲食，避免高糖食物",
            "保持規律運動",
            "記錄症狀變化"
        ],
        "need_doctor": true,
        "urgency": "medium"
    }
}
```

2. For non-matching symptoms:
```json
{
    "status": "success",
    "response": {
        "type": "unmatched",
        "title": "找不到完全相符的症狀",
        "message": "您描述的症狀（頭痛和高燒）需要更多資訊來判斷可能的疾病",
        "additional_info_needed": [
            "頭痛的具體位置和性質",
            "發燒的持續時間",
            "是否有其他症狀"
        ],
        "suggestions": [
            "提供更多症狀細節",
            "建議盡快就醫，因為高燒需要及時處理"
        ],
        "need_doctor": true,
        "urgency": "high"
    }
}
```

3. For unrelated questions:
```json
{
    "status": "success",
    "response": {
        "type": "unrelated",
        "title": "問題與疾病無關",
        "message": "您好，我是一個醫療顧問，主要協助回答健康相關的問題",
        "suggestions": [
            "如果您有任何關於健康或疾病的問題，我很樂意為您解答"
        ]
    }
}
```

## Deployment

Before commit, please ensure the `requirements.txt` align with the dependencies if you need:

```shell
uv pip compile pyproject.toml -o requirements.txt
```
