import requests
from bs4 import BeautifulSoup
import re
import json
import os
import time
import asyncio
from telegram import Bot
import logging


# Configure logging
logging.basicConfig(filename='bot.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s:%(message)s')

# Telegram settings
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# URL of the public Telegram chat
channel_url = "https://t.me/s/ArmyCAT1"
json_file = "database.json"
sector_watch = "3N"

# Load or initialize the JSON file
if os.path.exists(json_file):
    with open(json_file, "r") as f:
        processed_alerts = json.load(f)
else:
    processed_alerts = {}


async def send_message(message, image_url=None):
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        if image_url:
            await bot.send_photo(chat_id=CHAT_ID, photo=image_url, caption=message)
        else:
            await bot.send_message(chat_id=CHAT_ID, text=message)
        logging.info("Message sent to group.")
    except Exception as e:
        logging.error(f"Error sending message: {e}")


def get_channel_chat_id():
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates'
    response = requests.get(url)
    data = response.json()
    if not data['ok']:
        print("Failed to get updates.")
        return
    for result in data['result']:
        if 'channel_post' in result:
            chat = result['channel_post']['chat']
            chat_id = chat['id']
            chat_title = chat.get('title', 'N/A')
            print(f"Channel Chat ID: {chat_id}, Channel Name: {chat_title}")
            return chat_id
    print("No channel messages found in updates.")

# Function to check if a message is already processed
def is_message_processed(message_id):
    return str(message_id) in processed_alerts

# Function to store new message in the JSON file
def store_message(message_id, alert_time, area_codes):
    processed_alerts[str(message_id)] = {"alert_time": alert_time, "area_codes": area_codes}
    with open(json_file, "w") as f:
        json.dump(processed_alerts, f)

# Function to scrape the latest messages
def check_for_lightning_alert():

    messages_to_send = []
    response = requests.get(channel_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all messages in the chat
    messages = soup.find_all('div', class_='tgme_widget_message_text')

    for message in messages:
        text = message.get_text()
        # Use message text as a unique identifier or hash
        
        # get today's date
        today = time.strftime("%Y-%m-%d")
        message_id = f"{today}_{text}"

        # Check if the message has already been processed
        if is_message_processed(message_id):
            continue  # Skip already processed messages
        
        # If it's a new message, check for CAT 1 alerts
        if "CAT 1" in text:
            matches = re.findall(r'\((\d{4}-\d{4})\)\s*([\w,]+)', text, re.DOTALL)
            # print(matches)
            for match in matches:
                time_range, areas = match
                if sector_watch in areas.split(","):
                    message_to_send = f"⚡️ Lightning alert for {sector_watch}!\nTime: {time_range}"
                    print(message_to_send)
                    messages_to_send.append(message_to_send)

                    # Store the message in the JSON file to avoid duplicate alerts
                    store_message(message_id, time_range, sector_watch)

    return messages_to_send



# Run the function
if __name__ == '__main__':
    messages_to_send = check_for_lightning_alert()
    if messages_to_send:
        for message in messages_to_send:
            asyncio.run(send_message(message))
    else:
        logging.info("No new alerts found.")