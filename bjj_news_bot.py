import asyncio
import feedparser
import random
import requests
import base64
import json
import os
from datetime import datetime
from telegram.ext import Application
from urllib.parse import quote
from dotenv import load_dotenv
import logging

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения из .env файла
load_dotenv()

# Загрузка переменных из окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# Файлы
TOPICS_FILE = 'topics.txt'
FEEDS_FILE = 'feeds.txt'
QUOTES_FILE = 'quotes.txt'
USED_LINKS_FILE = 'used_links.txt'

def load_used_links():
    try:
        with open(USED_LINKS_FILE, 'r') as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()

def save_used_link(link):
    repo_owner = "jochifromborjigin"
    repo_name = "bjj_bot"
    file_path = "used_links.txt"
    branch = "main"
    token = os.getenv("bjj_bot")

    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        sha = data["sha"]
        decoded = base64.b64decode(data["content"]).decode()
        lines = set(decoded.strip().split("\n"))

        if link in lines:
            return

        lines.add(link)
        updated_content = "\n".join(lines)
        b64_content = base64.b64encode(updated_content.encode()).decode()

        update_data = {
            "message": f"Add used link: {link}",
            "content": b64_content,
            "sha": sha,
            "branch": branch
        }

        r = requests.put(api_url, headers=headers, data=json.dumps(update_data))
        r.raise_for_status()
        logger.info(f"✅ Ссылка сохранена: {link}")
    except requests.RequestException as e:
        logger.error(f"❌ Ошибка при работе с GitHub API: {e}")

# Проверка и создание файла used_links.txt если он отсутствует
if not os.path.exists(USED_LINKS_FILE):
    with open(USED_LINKS_FILE, 'w'):
        pass

used_links = load_used_links()

with open(TOPICS_FILE, 'r') as f:
    topics = [line.strip() for line in f.readlines()]

with open(QUOTES_FILE, 'r') as f:
    quotes = [line.strip() for line in f.readlines()]

week_number = datetime.now().isocalendar()[1]
current_topic = topics[(week_number - 1) % len(topics)]

application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

def find_article(topic):
    with open(FEEDS_FILE, 'r') as f:
        feed_urls = f.read().splitlines()

    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if topic.lower() in entry.title.lower() and entry.link not in used_links:
                save_used_link(entry.link)
                used_links.add(entry.link)
                return entry.link, entry.title

    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if entry.link not in used_links:
                save_used_link(entry.link)
                used_links.add(entry.link)
                return entry.link, entry.title
    return None, None

def find_video(topic):
    query = quote(f"{topic} BJJ")
    search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&key={YOUTUBE_API_KEY}&maxResults=5"
    response = requests.get(search_url).json()

    if 'items' in response:
        for item in response['items']:
            video_id = item['id']['videoId']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            video_title = item['snippet']['title']
            if video_url not in used_links:
                save_used_link(video_url)
                used_links.add(video_url)
                return video_url, video_title
    return None, None

async def send_post():
    article_link, article_title = find_article(current_topic)
    if article_link:
        text = f"🌅 Good morning, warriors!\n\nToday's focus: *{current_topic}*\n\n📖 Article: [{article_title}]({article_link})\n\nStay strong and keep learning! 💪 #BJJ"
    else:
        video_link, video_title = find_video(current_topic)
        if video_link:
            text = f"🎥 Video: [{video_title}]({video_link})\n\nVisualize and conquer! 🔥 #BJJ"
        else:
            quote = random.choice(quotes)
            text = f"🧠 Thought:\n\n_{quote}_\n\n#BJJ #Mindset"
    await application.bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=text, parse_mode="Markdown")

async def scheduler():
    while True:
        now = datetime.now()
        if now.hour == 12 and now.minute == 0:
            await send_post()
        await asyncio.sleep(60)

async def main():
    await application.initialize()
    await application.start()
    logger.info(f"🤖 BJJ Bot запущен! Тема недели: {current_topic}")
    await scheduler()

if __name__ == "__main__":
    asyncio.run(main())


