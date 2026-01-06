from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
import requests
import asyncio
import logging
import re
import os
from datetime import datetime

# Configuration from environment variables
URL = os.getenv("MONITOR_URL", "https://in.bookmyshow.com/movies/salem/jana-nayagan/buytickets/ET00430817/20260109")
SEARCH_TEXTS = os.getenv("SEARCH_TEXTS", "SPR,Aascars,Raajam").split(",")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "10"))  # Check every 10 seconds

# Telegram Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "8500066528:AAEmtoOfxN7iAopaf49wbqay3_wKWXEF3PE")
CHAT_ID = os.getenv("CHAT_ID", "-5061927536")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Ticket Monitor API")

# Global state to track monitoring
monitoring_status = {
    "is_running": False,
    "last_check": None,
    "total_checks": 0,
    "matches_found": 0,
    "last_matches": []
}

def send_telegram_message(message):
    """Sends a message to the configured Telegram chat."""
    if not BOT_TOKEN or not CHAT_ID:
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
            if re.search(r'<span[^>]*>[^<]*' + re.escape(text), response.text):
                found_matches.append(text)
        
        monitoring_status["last_check"] = datetime.now().isoformat()
        monitoring_status["total_checks"] += 1
        
        if found_matches:
            match_str = ", ".join(found_matches)
            logging.info(f"FOUND MATCHES: '{match_str}' are present in the booking list!")
            monitoring_status["matches_found"] += 1
            monitoring_status["last_matches"] = found_matches
            send_telegram_message(f"🚨 TICKETS AVAILABLE! 🚨\n\nFound the following cinemas:\n{match_str}\n\nLink:\n{URL}")
            return True
        else:
            logging.info(f"Not found in booking list (Footer matches ignored).")
            monitoring_status["last_matches"] = []
            return False

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching URL: {e}")
        return False

async def monitor_tickets_background():
    """Background task that continuously monitors tickets."""
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
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Ticket Monitor API",
        "endpoints": {
            "/status": "Get monitoring status",
            "/check": "Manually trigger a ticket check",
            "/start": "Start monitoring",
            "/stop": "Stop monitoring"
        }
    }

@app.get("/status")
async def get_status():
    """Get current monitoring status."""
    return JSONResponse(content={
        "status": "running" if monitoring_status["is_running"] else "stopped",
        "monitoring_url": URL,
        "search_texts": SEARCH_TEXTS,
        "check_interval": CHECK_INTERVAL,
        "last_check": monitoring_status["last_check"],
        "total_checks": monitoring_status["total_checks"],
        "matches_found": monitoring_status["matches_found"],
        "last_matches": monitoring_status["last_matches"]
    })

@app.post("/check")
async def manual_check():
    """Manually trigger a ticket check."""
    found = check_tickets()
    return JSONResponse(content={
        "checked": True,
        "found_matches": found,
        "last_matches": monitoring_status["last_matches"],
        "timestamp": datetime.now().isoformat()
    })

@app.post("/start")
async def start_monitoring(background_tasks: BackgroundTasks):
    """Start the monitoring process."""
    if monitoring_status["is_running"]:
        return JSONResponse(content={"message": "Monitoring is already running"})
    
    asyncio.create_task(monitor_tickets_background())
    return JSONResponse(content={"message": "Monitoring started"})

@app.post("/stop")
async def stop_monitoring():
    """Stop the monitoring process."""
    if not monitoring_status["is_running"]:
        return JSONResponse(content={"message": "Monitoring is not running"})
    
    monitoring_status["is_running"] = False
    return JSONResponse(content={"message": "Monitoring stopped"})

# For Vercel serverless function
app_handler = app
