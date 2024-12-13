# Spotify Playlist Stalker

Ever wanted to know when your friends adds new songs into their playlist?

## What is this? 🤔

This is a script that monitors a Spotify playlist and tells you when someone adds new music. 

## Features

- Stalks a playlist
- Sends you a Telegram message when a new song/songs are added
- Keeps a record of all tracks
- Docker support (because why not)

## Setup 🛠️

1. Create a `.env` file with your keys:
```env
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
PLAYLIST_ID=your_playlist_id_here
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

1. Install requirements (if you're not using Docker):
```bash
pip install -r requirements.txt
```

1. Or run with Docker:
```bash
docker build -t spotify-playlist-stalker .
docker run --env-file .env spotify-playlist-stalker
```

Remember: With great power comes great responsibility. Use this wisely.