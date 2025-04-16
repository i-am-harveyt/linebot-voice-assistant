# LineBot Voice Assistant

## Description

## Installation

### Prerequisite

Make sure

1. [ffmpeg](https://ffmpeg.org/)
2. [uv](https://docs.astral.sh/uv/)

is insalled on your computer

### Project Setup

#### Install dependencies:

```shell
uv install
```

#### Environment Setup

Get your line channel access token with:

```shell
curl -v -X POST https://api.line.me/oauth2/v3/token \
-H 'Content-Type: application/x-www-form-urlencoded' \
--data-urlencode 'grant_type=client_credentials' \
--data-urlencode 'client_id=<client-id>' \
--data-urlencode 'client_secret=<client-secret>'
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

### For Developers

Format the code with

```shell
uv run ruff format
```

## Deployment

Before commit, please ensure the `requirements.txt` align with the dependencies if you need:

```shell
uv pip freeze > requirements.txt
```
