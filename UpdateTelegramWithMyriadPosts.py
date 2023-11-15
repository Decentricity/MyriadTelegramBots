import json
import html
import requests
import re
from html import unescape
import time
from pathlib import Path
from telegram import Update, ParseMode
from telegram.ext import Updater, MessageHandler, Filters

def fetch_api_data():
    print("Attempting to fetch new posts from Myriad API...")
    response = requests.get("https://api.myriad.social//user/posts?pageLimit=1")
    if response.status_code == 200:
        print("Data fetched successfully!")
        return response.json()["data"]
    else:
        print(f"Failed to fetch data: HTTP {response.status_code}")
        return []

def load_cache(filename):
    print(f"Attempting to load data from {filename}...")
    if Path(filename).is_file():
        with open(filename, "r") as f:
            data = json.load(f)
            print("Data loaded successfully.")
            return data
    else:
        print(f"No cache file found for {filename}.")
        return []

def save_cache(data, filename):
    print(f"Saving new data to {filename}...")
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)
        print("Data saved successfully.")

def filter_new_posts(api_data, cache_data):
    print("Filtering out already cached posts...")
    cached_ids = [post["id"] for post in cache_data]
    new_posts = [post for post in api_data if post["id"] not in cached_ids]
    print(f"Found {len(new_posts)} new post(s).")
    return new_posts

import re
from html import unescape

def extract_content_and_media(post):
    # Extract text content
    text_content = post.get('text', '')

    # Extract all URLs, including those within iframe tags
    all_urls = re.findall(r'(http[s]?://\S+)', text_content)

    # Remove HTML tags and unescape HTML entities
    text_content = re.sub(r'<[^>]+>', '', text_content)
    text_content = unescape(text_content)

    # Construct clickable links for all extracted URLs
    links = [f"<a href='{url}'>{url}</a>" for url in all_urls]

    # Combine the text content with clickable links
    combined_content = f"{text_content}\n" + "\n".join(links)

    return combined_content.strip()

def pretty_print_post(post):
    try:
        post_content = extract_content_and_media(post)
        post_url = f"https://app.myriad.social/post/{post['id']}"
        user_name = post['user'].get('name', 'Unknown User')

        # Format the message as HTML
        formatted_message = (
            f"<b>{user_name}</b>\n"
            f"{post_content}\n"
            f"<a href='{post_url}'>View on Myriad</a>\n"
            f"----\n"
        )
        return formatted_message
    except Exception as e:
        return f"Failed to process post content for post ID {post.get('id', 'unknown')}: {e}"


def pretty_print_posts(posts, updater, chat_ids):
    for post in posts:
        formatted_post = pretty_print_post(post)
        send_to_group(updater, chat_ids, formatted_post)

def send_to_group(updater, chat_ids, message):
    if not chat_ids:
        print("The bot has not been added to any groups yet. Unable to send messages.")
        return
    for chat_id in chat_ids:
        try:
            updater.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML)
            print(f"Message sent to group {chat_id}.")
        except Exception as e:
            print(f"Failed to send to {chat_id}: {e}")

def group_handler(update, context):
    global chat_ids
    chat_id = update.message.chat_id
    if chat_id not in chat_ids:
        chat_ids.append(chat_id)
        save_cache(chat_ids, "chat_ids.json")
        print(f"Bot added to new group: {chat_id}")

def echo(update, context):
    print("Echoing received message...")
    print(json.dumps(update.to_dict(), indent=4))

def main():
    global chat_ids
    print("Bot is starting...")
    
    # Initialize Telegram bot
    updater = Updater(token='6073392763:AAEvxs2CIEWmT8Iv9bJQHplM8KQdiu6drow', use_context=True)
    dispatcher = updater.dispatcher


    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, group_handler))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    updater.start_polling()
    chat_ids = load_cache("chat_ids.json")

    while True:
        if not chat_ids:
            print("No groups detected. Waiting to be added to a Telegram group...")
            time.sleep(60)  # Wait a while before checking again
            continue

        api_data = fetch_api_data()
        cache_data = load_cache("cache.json")
        new_posts = filter_new_posts(api_data, cache_data)
        
        if new_posts:
            pretty_print_posts(new_posts, updater, chat_ids)
            # Only update the cache_data and save it after the posts have been sent to the group
            cache_data.extend(new_posts)
            save_cache(cache_data, "cache.json")
            print("New posts processed and cache updated.")
        else:
            print("No new Myriad posts detected at this time.")

        time.sleep(10)  # Wait for a minute before the next API call

if __name__ == "__main__":
    main()
