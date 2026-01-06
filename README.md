# Ticket Monitor - FastAPI Application

A FastAPI-based ticket monitoring service that continuously checks BookMyShow for ticket availability and sends Telegram notifications.

## Features

- 🔄 Continuous background monitoring
- 📱 Telegram notifications when tickets are found
- 🌐 RESTful API endpoints for control and status
- ☁️ Deployable on Vercel (with limitations - see below)

## Important Note about Vercel Deployment

**⚠️ Vercel Limitation**: Vercel serverless functions have a **maximum execution time of 10 seconds** on the free tier (60 seconds on Pro). This means **continuous background monitoring won't work reliably on Vercel**.

### Recommended Alternatives for Continuous Monitoring:

1. **Railway.app** (Recommended) - Supports long-running processes
2. **Render.com** - Free tier with always-on services
3. **Fly.io** - Good for background workers
4. **DigitalOcean App Platform** - Reliable for background tasks
5. **Local/VPS Server** - Most reliable for 24/7 monitoring

### Vercel Workaround Options:

If you still want to use Vercel, you can:

1. **Use External Cron Service**: Set up a service like:
   - **Cron-job.org** (free)
   - **EasyCron** (free tier available)
   - **GitHub Actions** (scheduled workflows)
   
   Configure it to call your `/check` endpoint every 10 seconds (or desired interval).

2. **Vercel Cron Jobs**: Use Vercel's built-in cron (limited to 1 minute minimum interval):
   - Add to `vercel.json`:
   ```json
   {
     "crons": [{
       "path": "/check",
       "schedule": "* * * * *"
     }]
   }
   ```

## Local Development

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file:
```bash
cp .env.example .env
```

3. Edit `.env` with your values:
```env
BOT_TOKEN=your_telegram_bot_token
CHAT_ID=your_telegram_chat_id
MONITOR_URL=https://in.bookmyshow.com/movies/...
SEARCH_TEXTS=SPR,Aascars
CHECK_INTERVAL=10
```

### Run Locally

```bash
uvicorn ticket_monitor:app --reload --host 0.0.0.0 --port 8000
```

Access the API at `http://localhost:8000`

## API Endpoints

### GET `/`
Returns API information and available endpoints.

### GET `/status`
Get current monitoring status including:
- Running state
- Last check time
- Total checks performed
- Matches found
- Last matched cinemas

Example response:
```json
{
  "status": "running",
  "monitoring_url": "https://...",
  "search_texts": ["SPR", "Aascars"],
  "last_check": "2026-01-06T10:30:00",
  "total_checks": 150,
  "matches_found": 5,
  "last_matches": ["SPR"]
}
```

### POST `/check`
Manually trigger a single ticket check.

### POST `/start`
Start the background monitoring process.

### POST `/stop`
Stop the background monitoring process.

## Deployment to Vercel (Limited Support)

### Prerequisites

1. Install Vercel CLI:
```bash
npm install -g vercel
```

2. Login to Vercel:
```bash
vercel login
```

### Deploy

1. Navigate to project directory:
```bash
cd /home/node/playground/ticketer
```

2. Deploy to Vercel:
```bash
vercel
```

3. Set environment variables in Vercel dashboard:
   - Go to your project settings
   - Navigate to "Environment Variables"
   - Add:
     - `BOT_TOKEN`
     - `CHAT_ID`
     - `MONITOR_URL`
     - `SEARCH_TEXTS`
     - `CHECK_INTERVAL`

4. Deploy to production:
```bash
vercel --prod
```

### Set Up External Cron (Recommended for Vercel)

Since Vercel doesn't support long-running processes, use an external cron service:

1. Go to https://cron-job.org (or similar service)
2. Create a new cron job
3. Set URL to: `https://your-app.vercel.app/check`
4. Set interval to every 10 seconds (or your preferred interval)
5. Set method to `POST`

## Deployment to Railway.app (Recommended)

Railway supports long-running processes and is better suited for this use case:

1. Install Railway CLI:
```bash
npm install -g @railway/cli
```

2. Login and initialize:
```bash
railway login
railway init
```

3. Add a `Procfile`:
```
web: uvicorn ticket_monitor:app --host 0.0.0.0 --port $PORT
```

4. Set environment variables:
```bash
railway variables set BOT_TOKEN=your_token
railway variables set CHAT_ID=your_chat_id
# ... other variables
```

5. Deploy:
```bash
railway up
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token | - |
| `CHAT_ID` | Telegram chat ID | - |
| `MONITOR_URL` | BookMyShow URL to monitor | Pre-configured URL |
| `SEARCH_TEXTS` | Comma-separated cinema names | SPR,Aascars |
| `CHECK_INTERVAL` | Seconds between checks | 10 |

### Getting Telegram Credentials

1. **Bot Token**:
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` and follow instructions
   - Copy the token provided

2. **Chat ID**:
   - Message [@userinfobot](https://t.me/userinfobot) on Telegram
   - Copy your chat ID
   - Or create a group, add the bot, and use the group ID

## Testing

Test the API locally:

```bash
# Check status
curl http://localhost:8000/status

# Manual check
curl -X POST http://localhost:8000/check

# Start monitoring
curl -X POST http://localhost:8000/start

# Stop monitoring
curl -X POST http://localhost:8000/stop
```

## Troubleshooting

### Vercel: Function timeout
- Use external cron service instead of background monitoring
- Consider alternative platforms (Railway, Render)

### No Telegram notifications
- Verify `BOT_TOKEN` and `CHAT_ID` are correct
- Ensure bot is added to group (if using group chat ID)
- Check bot has permission to send messages

### No matches found
- Verify the `MONITOR_URL` is correct
- Check `SEARCH_TEXTS` match exactly with cinema names
- Test manually by visiting the URL

## License

MIT
