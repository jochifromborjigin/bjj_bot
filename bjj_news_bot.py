# Импорт библиотек
import asyncio
import feedparser
import random
import schedule
import requests
import nest_asyncio
import subprocess
from datetime import datetime
from telegram.ext import Application

# Настройки токенов и файлов
import os

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

TOPICS_FILE = 'topics.txt'
FEEDS_FILE = 'feeds.txt'
QUOTES_FILE = 'quotes.txt'
USED_LINKS_FILE = 'used_links.txt'

# Загрузка использованных ссылок
def load_used_links():
    try:
        with open(USED_LINKS_FILE, 'r') as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()

def save_used_link(link):
    with open(USED_LINKS_FILE, 'a') as f:
        f.write(link + '\n')

    try:
        subprocess.run(["git", "config", "--global", "user.name", "bjj-bot"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "bjj-bot@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", USED_LINKS_FILE], check=True)
        subprocess.run(["git", "commit", "-m", f"Add used link: {link}"], check=True)
        subprocess.run(
            ["git", "push", f"https://{os.getenv('bjj_bot')}@github.com/jochifromborjigin/bjj_bot.git"],
            check=True,
        )
        print(f"✅ Git pushed link: {link}")
    except Exception as e:
        print(f"❌ Git push failed: {e}")

# Проверка и создание файла used_links.txt если он отсутствует
if not os.path.exists(USED_LINKS_FILE):
    with open(USED_LINKS_FILE, 'w') as f:
        pass  # Просто создаём пустой файл
        
used_links = load_used_links()

# Загрузка тем недели
with open(TOPICS_FILE, 'r') as f:
    topics = [line.strip() for line in f.readlines()]

# Загрузка цитат
with open(QUOTES_FILE, 'r') as f:
    quotes = [line.strip() for line in f.readlines()]

# Определяем текущую тему недели
week_number = datetime.now().isocalendar()[1]
current_topic = topics[(week_number - 1) % len(topics)]

# Инициализация Telegram-бота
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Поиск статьи
def find_article(topic, used_links):
    with open(FEEDS_FILE, 'r') as f:
        feed_urls = f.read().splitlines()

    # Сначала ищем по теме
    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if topic.lower() in entry.title.lower() and entry.link not in used_links:
                save_used_link(entry.link)
                used_links.add(entry.link)
                return entry.link, entry.title

    # Ищем любую статью
    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if entry.link not in used_links:
                save_used_link(entry.link)
                used_links.add(entry.link)
                return entry.link, entry.title

    return None, None

# Поиск подкаста
def find_podcast(topic, used_links):
    with open(FEEDS_FILE, 'r') as f:
        feed_urls = f.read().splitlines()

    # Сначала ищем подкаст по теме
    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if ('podcast' in entry.title.lower() or 'episode' in entry.title.lower()) and topic.lower() in entry.title.lower() and entry.link not in used_links:
                save_used_link(entry.link)
                used_links.add(entry.link)
                return entry.link, entry.title

    # Ищем любой подкаст
    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if ('podcast' in entry.title.lower() or 'episode' in entry.title.lower()) and entry.link not in used_links:
                save_used_link(entry.link)
                used_links.add(entry.link)
                return entry.link, entry.title

    return None, None

# Поиск видео через YouTube API
def find_video(topic, used_links):
    search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={topic} BJJ&type=video&key={YOUTUBE_API_KEY}&maxResults=5"
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

    # Ищем любой BJJ-видео, если по теме нет
    fallback_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q=BJJ&type=video&key={YOUTUBE_API_KEY}&maxResults=5"
    fallback_response = requests.get(fallback_url).json()

    if 'items' in fallback_response:
        for item in fallback_response['items']:
            video_id = item['id']['videoId']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            video_title = item['snippet']['title']
            if video_url not in used_links:
                save_used_link(video_url)
                used_links.add(video_url)
                return video_url, video_title

    return None, None

# Утренний пост: статья или цитата
async def send_morning_post():
    article_link, article_title = find_article(current_topic, used_links)
    if article_link:
        text = f"🌅 Good morning, warriors!\n\nToday's focus: *{current_topic}*\n\n📖 Article: [{article_title}]({article_link})\n\nStay strong and keep learning! 💪 #BJJ"
    else:
        video_link, video_title = find_video(current_topic, used_links)
        if video_link:
            text = f"🌅 Good morning, warriors!\n\nToday's resource on *{current_topic}*:\n\n🎥 Video: [{video_title}]({video_link})\n\nVisualize and conquer! 🔥 #BJJ"
        else:
            quote = random.choice(quotes)
            text = f"🌅 Good morning, warriors!\n\n*Motivational thought:*\n\n_{quote}_\n\n#BJJ #Mindset"
    await application.bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=text, parse_mode="Markdown")

# Дневной пост: подкаст или цитата
async def send_afternoon_post():
    podcast_link, podcast_title = find_podcast(current_topic, used_links)
    if podcast_link:
        text = f"🎧 Midday learning time!\n\nTopic: *{current_topic}*\n\n🎙️ Podcast: [{podcast_title}]({podcast_link})\n\nSharpen your mind while you rest! 🧠 #BJJ"
    else:
        video_link, video_title = find_video(current_topic, used_links)
        if video_link:
            text = f"🎧 Midday resource on *{current_topic}*:\n\n🎥 Video: [{video_title}]({video_link})\n\nLearn, adapt, evolve! 🚀 #BJJ"
        else:
            quote = random.choice(quotes)
            text = f"🎧 Midday break inspiration!\n\n*Quote:*\n\n_{quote}_\n\n#BJJ #Inspiration"
            
    await application.bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=text, parse_mode="Markdown")

# Вечерний пост: видео или цитата
async def send_evening_post():
    video_link, video_title = find_video(current_topic, used_links)
    if video_link:
        text = f"🌙 Night drilling!\n\nFocus: *{current_topic}*\n\n🎥 Video: [{video_title}]({video_link})\n\nVisualize. Drill. Improve! 🔥 #BJJ"
    else:
        quote = random.choice(quotes)
        text = f"🌙 Night inspiration!\n\n*Reflection:*\n\n_{quote}_\n\n#BJJ #Philosophy"

    await application.bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=text, parse_mode="Markdown")

# Планирование постов
schedule.every().day.at("12:00").do(lambda: asyncio.ensure_future(send_morning_post()))
schedule.every().day.at("18:00").do(lambda: asyncio.ensure_future(send_afternoon_post()))
schedule.every().day.at("00:00").do(lambda: asyncio.ensure_future(send_evening_post()))

# Основной цикл
async def scheduler_loop():
    while True:
        schedule.run_pending()
        await asyncio.sleep(10)

async def main():
    await application.initialize()
    await application.start()
    print(f"🤖 BJJ Daily News Bot is running! Current topic: {current_topic}")
    await scheduler_loop()

if __name__ == "__main__":
    asyncio.run(main())


