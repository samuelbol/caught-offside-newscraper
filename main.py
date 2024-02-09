from keep_alive import keep_alive
import pytz
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup
from pymongo import MongoClient
import os

connection_string = os.environ.get("connection_string")
client = MongoClient(connection_string)

# Replace 'your_database_name' and 'your_collection_name' with actual names
db = client['chelsea_news']
collection = db['caught_offside']

HEADER = {
    "User-Agent":
        "Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36"
}

BOT_TOKEN = os.environ.get("bot_token")
CHAT_ID = os.environ.get("chat_id")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

keep_alive()
nigerian_tz = pytz.timezone("Africa/Lagos")


def scrape_caught_off_chls():
    url = "https://www.caughtoffside.com/tags/premier-league/chelsea/"
    response = requests.get(url, headers=HEADER, timeout=(10, 27))
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    news_cards = soup.find_all(
        "div", class_="col-s-12 col-m-6 post-container post-standard")
    news_list = []

    for news_card in news_cards[:10]:
        crd_title = news_card.find("div",
                                   class_="img-txt c-std-mgn-b std-pad").a.text
        crd_img = news_card.find("picture").img.get('data-src', '')

        crd_link = news_card.find("div",
                                  class_="img-txt c-std-mgn-b std-pad").a.get(
            'href', '')

        if not crd_title or not crd_img or not crd_link:
            continue

        resp = requests.get(f"https://www.caughtoffside.com{crd_link}",
                            headers=HEADER,
                            timeout=(10, 27))
        resp.raise_for_status()  # Check for HTTP status code errors
        soup = BeautifulSoup(resp.content, "html.parser")

        card_contd = (soup.find("div", {"id": "article-body"})).find_all("p")
        card_desc = card_contd[0].get_text() + "\n"
        card_desc += card_contd[1].get_text()

        news_list.append({
            "title": crd_title,
            "image": crd_img,
            "contents": card_desc
        })

    return news_list


# Function to send news to Telegram
def send_news_to_telegram(article_items):
    for item in article_items:
        title_ = item.get("title", "")
        story_ = item.get("contents", "")
        img_ = item.get("image", "")

        # Check if any of the required data is missing
        if not title_ or not story_:
            continue

        message = f"🚨 *{title_}*\n\n{story_}\n\n" \
                  f"_(via CaughtOffside)_\n\n" \
                  f"📲 @JustCFC"

        saved_titles = collection.find_one({"text": title_})
        if not saved_titles:
            response = requests.post(BASE_URL + "sendPhoto",
                                     json={
                                         "chat_id": CHAT_ID,
                                         "disable_web_page_preview": False,
                                         "parse_mode": "Markdown",
                                         "caption": message,
                                         "photo": img_
                                     })

            if response.status_code == 200:
                print("Message sent successfully.")

            else:
                print(
                    f"Message sending failed. Status code: {response.status_code}"
                )


def main():
    news_items = scrape_caught_off_chls()
    send_news_to_telegram(news_items)


scheduler = BlockingScheduler(timezone=nigerian_tz)
scheduler.add_job(main, "interval", minutes=30)
scheduler.start()
# main()
