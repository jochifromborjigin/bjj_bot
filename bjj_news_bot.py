# Импорт библиотек
import asyncio
import feedparser
import random
import schedule
import requests
import nest_asyncio
from datetime import datetime
from telegram.ext import Application

# Применение nest_asyncio для Jupyter
nest_asyncio.apply()

# Настройки токенов и файлов
TELEGRAM_BOT_TOKEN = '7611379154:AAHZ_0MS34zrt3BTkl3unT4byKHTfVkdh6E'
TELEGRAM_CHANNEL_ID = '@bjjdailynews'
YOUTUBE_API_KEY = 'AIzaSyA0Y6oa9EmsOjHfLR1IrEPtYCWUiz2Vuks'

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

used_links = load_used_links()

# Загрузка тем недели
with open(TOPICS_FILE, 'r') as f:
    topics = [line.strip() for line in f.readlines()]

# Загрузка цитат
with open(QUOTES_FILE, 'r') as f:
    quotes = [line.strip() for line in f.readlines()]

# Определяем текущую тему недели
week_number = datetime.utcnow().isocalendar()[1]
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
                return entry.link, entry.title

    # Ищем любую статью
    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if entry.link not in used_links:
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
                return entry.link, entry.title

    # Ищем любой подкаст
    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if ('podcast' in entry.title.lower() or 'episode' in entry.title.lower()) and entry.link not in used_links:
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
                return video_url, video_title

    return None, None


# Утренний пост: статья или цитата
async def send_morning_post():
    article_link, article_title = find_article(current_topic, used_links)
    if article_link:
        text = f"🌅 Good morning, warriors!\n\nToday's focus: *{current_topic}*\n\n📖 Article: [{article_title}]({article_link})\n\nStay strong and keep learning! 💪 #BJJ"
        save_used_link(article_link)
    else:
        quote = random.choice(quotes)
        text = f"🌅 Good morning, warriors!\n\n*Motivational thought:*\n\n_{quote}_\n\n#BJJ #Mindset"

    await application.bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=text, parse_mode="Markdown")

# Дневной пост: подкаст или цитата
async def send_afternoon_post():
    podcast_link, podcast_title = find_podcast(current_topic, used_links)
    if podcast_link:
        text = f"🎧 Midday learning time!\n\nTopic: *{current_topic}*\n\n🎙️ Podcast: [{podcast_title}]({podcast_link})\n\nSharpen your mind while you rest! 🧠 #BJJ"
        save_used_link(podcast_link)
    else:
        quote = random.choice(quotes)
        text = f"🎧 Midday break inspiration!\n\n*Quote:*\n\n_{quote}_\n\n#BJJ #Inspiration"

    await application.bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=text, parse_mode="Markdown")

# Вечерний пост: видео или цитата
async def send_evening_post():
    video_link, video_title = find_video(current_topic, used_links)
    if video_link:
        text = f"🌙 Night drilling!\n\nFocus: *{current_topic}*\n\n🎥 Video: [{video_title}]({video_link})\n\nVisualize. Drill. Improve! 🔥 #BJJ"
        save_used_link(video_link)
    else:
        quote = random.choice(quotes)
        text = f"🌙 Night inspiration!\n\n*Reflection:*\n\n_{quote}_\n\n#BJJ #Philosophy"

    await application.bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=text, parse_mode="Markdown")

# Планирование постов
schedule.every().day.at("08:00").do(lambda: asyncio.ensure_future(send_morning_post()))
schedule.every().day.at("14:00").do(lambda: asyncio.ensure_future(send_afternoon_post()))
schedule.every().day.at("20:00").do(lambda: asyncio.ensure_future(send_evening_post()))

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

await main()
