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
uv install
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

## Deployment

Before commit, please ensure the `requirements.txt` align with the dependencies if you need:

```shell
uv pip compile pyproject.toml -o requirements.txt
```
