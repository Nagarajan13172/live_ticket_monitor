from flask import Flask, jsonify
import requests
import time
import logging
import re
import threading
import random
from datetime import datetime

app = Flask(__name__)

# Configuration
URL = "https://in.bookmyshow.com/movies/salem/jana-nayagan/buytickets/ET00430817/20260109"
SEARCH_TEXTS = ["SPR", "Aascars", "Raajam", "ROX"]
CHECK_INTERVAL = 60  # Check every 60 seconds (1 minute)

# Telegram Configuration
BOT_TOKEN = "8500066528:AAEmtoOfxN7iAopaf49wbqay3_wKWXEF3PE"
CHAT_ID = "-5061927536"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Global monitoring status
monitoring_status = {
    "is_running": False,
    "last_check": None,
    "total_checks": 0,
    "matches_found": 0,
    "last_matches": [],
    "errors": 0
}

# Session for connection reuse
session = requests.Session()

# User agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

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
    
    # Rotate user agent and add random delay (2-4 seconds to appear more human)
    user_agent = random.choice(USER_AGENTS)
    time.sleep(random.uniform(2, 4))
    
    # More realistic browser headers with random referer
    referers = [
        "https://www.google.com/",
        "https://www.google.co.in/",
        "https://in.bookmyshow.com/",
        ""
    ]
    
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en-IN;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document"
    }
    
    # Add referer randomly
    if random.choice([True, False]):
        headers["Referer"] = random.choice(referers)

    try:
        # Clear session cookies occasionally
        if random.randint(1, 5) == 1:
            session.cookies.clear()
        
        response = session.get(URL, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        logging.info(f"Page loaded: {len(response.text)} characters")
        
        found_matches = []
        for text in SEARCH_TEXTS:
            text = text.strip()
            # Search anywhere in the HTML (case-insensitive)
            if re.search(re.escape(text), response.text, re.IGNORECASE):
                match_count = len(re.findall(re.escape(text), response.text, re.IGNORECASE))
                logging.info(f"Found '{text}' {match_count} times in the page")
                found_matches.append(text)
            else:
                logging.info(f"'{text}' NOT found in the page")
        
        monitoring_status["last_check"] = datetime.now().isoformat()
        monitoring_status["total_checks"] += 1
        
        if found_matches:
            match_str = ", ".join(found_matches)
            logging.info(f"🎉 FOUND MATCHES: '{match_str}' are present in the booking list!")
            monitoring_status["matches_found"] += 1
            monitoring_status["last_matches"] = found_matches
            send_telegram_message(f"🚨 TICKETS AVAILABLE! 🚨\n\nFound the following cinemas:\n{match_str}\n\nLink:\n{URL}")
            return True
        else:
            logging.info(f"✓ Checked successfully - No matches found")
            monitoring_status["last_matches"] = []
            return False

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logging.warning(f"⚠️  403 Forbidden - Website blocking request. Will retry with different user agent...")
        else:
            logging.error(f"❌ HTTP Error: {e}")
        monitoring_status["errors"] += 1
        return False
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error fetching URL: {e}")
        monitoring_status["errors"] += 1
        return False

def monitor_tickets_background():
    """Background monitoring loop."""
    monitoring_status["is_running"] = True
    logging.info("Starting Ticket Monitor...")
    logging.info(f"Target URL: {URL}")
    logging.info(f"Search Texts: {SEARCH_TEXTS}")
    
    while monitoring_status["is_running"]:
        check_tickets()
        time.sleep(CHECK_INTERVAL)

@app.route('/')
def home():
    """Root endpoint."""
    return jsonify({
        "message": "Ticket Monitor API",
        "endpoints": {
            "/status": "Get monitoring status",
            "/check": "Manually trigger a check",
            "/start": "Start monitoring",
            "/stop": "Stop monitoring"
        }
    })

@app.route('/status')
def status():
    """Get monitoring status."""
    return jsonify({
        "status": "running" if monitoring_status["is_running"] else "stopped",
        "monitoring_url": URL,
        "search_texts": SEARCH_TEXTS,
        "check_interval": CHECK_INTERVAL,
        "last_check": monitoring_status["last_check"],
        "total_checks": monitoring_status["total_checks"],
        "matches_found": monitoring_status["matches_found"],
        "last_matches": monitoring_status["last_matches"],
        "errors": monitoring_status["errors"]
    })

@app.route('/check')
def manual_check():
    """Manually trigger a check."""
    found = check_tickets()
    return jsonify({
        "checked": True,
        "found_matches": found,
        "last_matches": monitoring_status["last_matches"],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/start')
def start_monitoring():
    """Start background monitoring."""
    if monitoring_status["is_running"]:
        return jsonify({"message": "Monitoring is already running"})
    
    thread = threading.Thread(target=monitor_tickets_background, daemon=True)
    thread.start()
    return jsonify({"message": "Monitoring started"})

@app.route('/stop')
def stop_monitoring():
    """Stop background monitoring."""
    if not monitoring_status["is_running"]:
        return jsonify({"message": "Monitoring is not running"})
    
    monitoring_status["is_running"] = False
    return jsonify({"message": "Monitoring stopped"})

# Start background monitoring when the app loads (for Gunicorn)
def start_background_monitoring():
    """Initialize background monitoring thread."""
    if not monitoring_status["is_running"]:
        monitor_thread = threading.Thread(target=monitor_tickets_background, daemon=True)
        monitor_thread.start()
        logging.info("Background monitoring initialized")

# Auto-start monitoring when module loads
start_background_monitoring()

if __name__ == "__main__":
    # Start Flask app (for local development)
    app.run(host='0.0.0.0', port=8080)
