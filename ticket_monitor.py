from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
import asyncio
import logging
import re
import random
import time
from datetime import datetime
import uvicorn
import cloudscraper

app = FastAPI(title="Ticket Monitor API")

# Configuration
URL = "https://in.bookmyshow.com/movies/salem/jana-nayagan/buytickets/ET00430817/20260109"
SEARCH_TEXTS = ["SPR", "Aascars", "Raajam", "ROX"]
CHECK_INTERVAL = 120  # Check every 120 seconds (2 minutes)

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
    "errors": 0,
    "consecutive_403s": 0
}

# Use cloudscraper instead of regular requests to bypass Cloudflare/anti-bot
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    }
)

# User agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
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
    
    # Add random delay (2-4 seconds to appear more human)
    time.sleep(random.uniform(2, 4))

    try:
        # Use cloudscraper which automatically handles JavaScript challenges
        response = scraper.get(URL, timeout=30)
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
            monitoring_status["consecutive_403s"] = 0  # Reset on success
            send_telegram_message(f"🚨 TICKETS AVAILABLE! 🚨\n\nFound the following cinemas:\n{match_str}\n\nLink:\n{URL}")
            return True
        else:
            logging.info(f"✓ Checked successfully - No matches found")
            monitoring_status["last_matches"] = []
            monitoring_status["consecutive_403s"] = 0  # Reset on success
            return False

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            monitoring_status["consecutive_403s"] += 1
            # Increase wait time after consecutive 403s
            if monitoring_status["consecutive_403s"] >= 3:
                extra_wait = monitoring_status["consecutive_403s"] * 30
                logging.warning(f"⚠️  Multiple 403 errors ({monitoring_status['consecutive_403s']}). Adding {extra_wait}s extra delay...")
                time.sleep(extra_wait)
            else:
                logging.warning(f"⚠️  403 Forbidden - Website blocking request. Will retry with different user agent...")
        else:
            logging.error(f"❌ HTTP Error: {e}")
        monitoring_status["errors"] += 1
        return False
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error fetching URL: {e}")
        monitoring_status["errors"] += 1
        return False

async def monitor_tickets_background():
    """Background monitoring loop."""
    monitoring_status["is_running"] = True
    logging.info("Starting Ticket Monitor...")
    logging.info(f"Target URL: {URL}")
    logging.info(f"Search Texts: {SEARCH_TEXTS}")
    
    while monitoring_status["is_running"]:
        check_tickets()
        await asyncio.sleep(CHECK_INTERVAL)

@app.on_event("startup")
async def startup_event():
    """Start monitoring on app startup."""
    asyncio.create_task(monitor_tickets_background())
    logging.info("Ticket monitoring started on startup")

@app.get("/")
async def home():
    """Root endpoint."""
    return {
        "message": "Ticket Monitor API",
        "endpoints": {
            "/status": "Get monitoring status",
            "/check": "Manually trigger a check",
            "/start": "Start monitoring",
            "/stop": "Stop monitoring"
        }
    }

@app.get("/status")
async def status():
    """Get monitoring status."""
    return JSONResponse(content={
        "status": "running" if monitoring_status["is_running"] else "stopped",
        "monitoring_url": URL,
        "search_texts": SEARCH_TEXTS,
        "check_interval": CHECK_INTERVAL,
        "last_check": monitoring_status["last_check"],
        "total_checks": monitoring_status["total_checks"],
        "matches_found": monitoring_status["matches_found"],
        "last_matches": monitoring_status["last_matches"],
        "errors": monitoring_status["errors"],
        "consecutive_403s": monitoring_status["consecutive_403s"]
    })

@app.post("/check")
async def manual_check():
    """Manually trigger a check."""
    found = check_tickets()
    return JSONResponse(content={
        "checked": True,
        "found_matches": found,
        "last_matches": monitoring_status["last_matches"],
        "timestamp": datetime.now().isoformat()
    })

@app.post("/start")
async def start_monitoring():
    """Start background monitoring."""
    if monitoring_status["is_running"]:
        return JSONResponse(content={"message": "Monitoring is already running"})
    
    asyncio.create_task(monitor_tickets_background())
    return JSONResponse(content={"message": "Monitoring started"})

@app.post("/stop")
async def stop_monitoring():
    """Stop background monitoring."""
    if not monitoring_status["is_running"]:
        return JSONResponse(content={"message": "Monitoring is not running"})
    
    monitoring_status["is_running"] = False
    return JSONResponse(content={"message": "Monitoring stopped"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
