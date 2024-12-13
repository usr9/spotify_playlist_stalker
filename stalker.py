from datetime import datetime, timedelta
import csv
import json
import os
from pathlib import Path
from typing import Dict, List

import httpx
from dotenv import load_dotenv

load_dotenv()


async def get_spotify_token() -> str:
    auth_url = 'https://accounts.spotify.com/api/token'
    auth_data = {
        'grant_type': 'client_credentials',
        'client_id': os.getenv('SPOTIFY_CLIENT_ID'),
        'client_secret': os.getenv('SPOTIFY_CLIENT_SECRET'),
    }

    if not auth_data['client_id'] or not auth_data['client_secret']:
        raise ValueError("Spotify credentials not found in environment variables")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(auth_url, data=auth_data)
            response.raise_for_status()
            return response.json()['access_token']
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise ValueError("Invalid Spotify credentials")
        elif e.response.status_code == 429:
            raise RuntimeError("Rate limit exceeded. Try again later")
        else:
            raise RuntimeError(f"Spotify API error: {e.response.status_code}")
    except httpx.RequestError as e:
        raise ConnectionError(f"Network error while connecting to Spotify: {str(e)}")
    except KeyError:
        raise ValueError("Unexpected response format from Spotify")


async def get_playlist_tracks(token: str) -> List[Dict]:
    playlist_id = os.getenv('PLAYLIST_ID')
    if not playlist_id:
        raise ValueError("Playlist ID not found in environment variables")

    playlist_url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    headers = {'Authorization': f'Bearer {token}'}
    
    tracks = []
    async with httpx.AsyncClient() as client:
        while playlist_url:
            try:
                response = await client.get(playlist_url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                for item in data['items']:
                    try:
                        track = item['track']
                        if track is None:  # Handle deleted tracks
                            continue
                        tracks.append({
                            'id': track['id'],
                            'name': track['name'],
                            'artist': track['artists'][0]['name'] if track['artists'] else 'Unknown Artist',
                            'url': track['external_urls']['spotify']
                        })
                    except (KeyError, IndexError) as e:
                        print(f"Error processing track: {str(e)}")
                        continue
                
                playlist_url = data.get('next')
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise ValueError("Invalid or expired token")
                elif e.response.status_code == 403:
                    raise ValueError("Insufficient permissions to access playlist")
                elif e.response.status_code == 404:
                    raise ValueError("Playlist not found")
                elif e.response.status_code == 429:
                    raise RuntimeError("Rate limit exceeded. Try again later")
                else:
                    raise RuntimeError(f"Spotify API error: {e.response.status_code}")
            except httpx.RequestError as e:
                raise ConnectionError(f"Network error while fetching playlist: {str(e)}")
            except json.JSONDecodeError:
                raise ValueError("Invalid response format from Spotify")
    
    if not tracks:
        print("Warning: No tracks found in playlist")
    
    return tracks


def load_existing_tracks(csv_path: Path) -> List[Dict]:
    if not csv_path.exists():
        return []
    
    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def save_tracks(tracks: List[Dict], csv_path: Path) -> None:
    fieldnames = ['id', 'name', 'artist', 'url']
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(tracks)


async def send_telegram_message(message: str) -> None:
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not telegram_token or not telegram_chat_id:
        raise ValueError("Telegram credentials not found in environment variables")

    telegram_url = f'https://api.telegram.org/bot{telegram_token}/sendMessage'
    data = {
        'chat_id': telegram_chat_id,
        'text': message,
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(telegram_url, data=data)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise ValueError("Invalid Telegram bot token")
        elif e.response.status_code == 400:
            raise ValueError("Invalid chat ID or message format")
        elif e.response.status_code == 429:
            raise RuntimeError("Too many requests to Telegram API")
        else:
            raise RuntimeError(f"Telegram API error: {e.response.status_code}")
    except httpx.RequestError as e:
        raise ConnectionError(f"Network error while sending Telegram message: {str(e)}")


def format_tracks_message(tracks: List[Dict]) -> str:
    messages = []
    messages.append("Looks like your friends have added some new songs to the playlist.")
    for track in tracks:
        messages.append(f"{track['name']} - {track['artist']}\n{track['url']}")
    return "\n\n".join(messages)


async def main() -> None:
    csv_path = Path('data/playlist_songs.csv')
    
    try:
        token = await get_spotify_token()
        current_tracks = await get_playlist_tracks(token)
        existing_tracks = load_existing_tracks(csv_path)
        
        existing_ids = {track['id'] for track in existing_tracks}
        new_tracks = [track for track in current_tracks if track['id'] not in existing_ids]
        
        if new_tracks:
            print("New songs found:")
            for track in new_tracks:
                print(f"\nNew song: {track['name']}")
                print(f"Artist: {track['artist']}")
                print(f"URL: {track['url']}")

            message = format_tracks_message(new_tracks)
            await send_telegram_message(message)
            save_tracks(current_tracks, csv_path)
        else:
            print("No new songs found.")
            
    except httpx.HTTPError as e:
        print(f"HTTP error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())