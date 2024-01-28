from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup
from keep_alive import keep_alive
from pytz import utc
import requests
import os

HEADER = {
    "User-Agent":
    "Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36"
}

BOT_TOKEN = os.environ.get('bot_token')
CHAT_ID = os.environ.get('chat_id')
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

keep_alive()


def scrape_caught_off_chls():
    url = "https://www.caughtoffside.com/tags/premier-league/chelsea/"
    response = requests.get(url, headers=HEADER, timeout=(10, 27))
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    news_cards = soup.find_all(
        "div", class_="col-s-12 col-m-6 post-container post-standard")
    news_list = []

    for news_card in news_cards[:5]:
        crd_title = news_card.find("div",
                                   class_="img-txt c-std-mgn-b std-pad").a.text
        crd_img = news_card.find("picture").img.get('data-src', '')

        crd_link = news_card.find("div",
                                  class_="img-txt c-std-mgn-b std-pad").a.get(
                                      'href', '')

        if not crd_title or not crd_img or not crd_link:
            continue

        try:
            with open("./logfile.txt", "r") as file:
                saved_titles = [line.rstrip("\n") for line in file.readlines()]
                if crd_title in saved_titles:
                    continue
        except FileNotFoundError:
            pass

        resp = requests.get(f"https://www.caughtoffside.com{crd_link}",
                            headers=HEADER,
                            timeout=(10, 27))
        resp.raise_for_status()  # Check for HTTP status code errors
        soup = BeautifulSoup(resp.content, "html.parser")

        card_contd = (soup.find("div", {"id": "article-body"})).find_all("p")
        card_desc = "".join([
            content.get_text(strip=True) + '\n\n' for content in card_contd[:3]
        ])
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

        message = f"🚨 *{title_}*\n\n{story_}\n" \
                  f"🔗 *CaughtOffside*\n\n" \
                  f"📲 @JustCFC"
        # print(message)
        try:
            with open("./logfile.txt", "r", encoding='utf-8') as file:
                saved_titles = [line.rstrip("\n") for line in file.readlines()]
        except FileNotFoundError:
            saved_titles = []

        if title_ not in saved_titles:
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

                with open("./logfile.txt", "a", encoding='utf-8') as file:
                    file.write(f"{title_}\n")

            else:
                print(response.text)
                print(
                    f"Message sending failed. Status code: {response.status_code}"
                )


def main():
    news_items = scrape_caught_off_chls()
    send_news_to_telegram(news_items)


scheduler = BlockingScheduler(timezone=utc)
scheduler.add_job(main, "interval", minutes=5)
# scheduler.start()
main()
