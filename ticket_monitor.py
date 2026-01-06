import requests
import time
import logging
import re

# Configuration
URL = "https://in.bookmyshow.com/movies/salem/jana-nayagan/buytickets/ET00430817/20260109"
SEARCH_TEXTS = ["SPR", "Aascars"]
CHECK_INTERVAL = 10  # Check every 10 seconds

# Telegram Configuration - REPLACE THESE WITH YOUR VALUES
BOT_TOKEN = "8500066528:AAEmtoOfxN7iAopaf49wbqay3_wKWXEF3PE"
CHAT_ID = "-5061927536"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def send_telegram_message(message):
    """Sends a message to the configured Telegram chat."""
    if BOT_TOKEN == "YOUR_BOT_TOKEN" or CHAT_ID == "YOUR_CHAT_ID":
        logging.warning("Telegram configuration missing. Skipping notification.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logging.info("Telegram notification sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")

def check_tickets():
    """Checks the URL for the search texts."""
    logging.info(f"Checking URL: {URL}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Ch-Ua": '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    try:
        response = requests.get(URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        found_matches = []
        for text in SEARCH_TEXTS:
            # Use Regex to find text inside a <span> tag.
            # This avoids matching the <a> tag in the footer.
            if re.search(r'<span[^>]*>[^<]*' + re.escape(text), response.text):
                found_matches.append(text)
        
        if found_matches:
            match_str = ", ".join(found_matches)
            logging.info(f"FOUND MATCHES: '{match_str}' are present in the booking list!")
            send_telegram_message(f"🚨 TICKETS AVAILABLE! 🚨\n\nFound the following cinemas:\n{match_str}\n\nLink:\n{URL}")
        else:
            logging.info(f"Not found in booking list (Footer matches ignored).")

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching URL: {e}")

def main():
    """Main loop."""
    logging.info("Starting Ticket Monitor...")
    logging.info(f"Target URL: {URL}")
    logging.info(f"Search Texts: {SEARCH_TEXTS}")

    while True:
        check_tickets()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
