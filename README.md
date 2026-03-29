# Omakase Booking Bot

Automated booking bot for [Omakase.in](https://omakase.in) restaurants. Monitors slot availability and auto-books when matching slots open — built for hard-to-reserve restaurants like Sugita Sushi and Sanshin Sushi.

## Features

- **Browser automation** — Playwright-based bot that navigates Omakase.in like a real user
- **Priority waterfall booking** — Rank your preferred (date, time) slots; bot tries them in order and stops on first success
- **Multi-restaurant targets** — Monitor multiple restaurants simultaneously with priority ordering
- **Anti-double-booking** — Immediately halts all attempts once a booking succeeds
- **Real-time dashboard** — Next.js frontend with live status, activity feed, and full configuration UI
- **Telegram notifications** — Instant alerts for slot found, booking confirmed, errors
- **Drag-to-reorder preferences** — Visual slot priority management in the UI

## Architecture

| Component | Technology |
|-----------|------------|
| Bot Engine | Python + Playwright |
| Backend API | Python + FastAPI |
| Frontend | Next.js 14 + TypeScript + Tailwind + shadcn/ui |
| Database | SQLite |
| Notifications | Telegram |
| Deployment | Docker Compose |

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/alfredkzr/omakase-booking-bot.git
cd omakase-booking-bot

# 2. Copy and configure environment
cp .env.example .env
# Edit .env with your encryption key (see .env.example for instructions)

# 3. Run with Docker Compose
docker compose up --build

# 4. Open the dashboard
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

## Setup

1. **Configure credentials** — Go to Settings page, enter your Omakase.in email/password
2. **Set up Telegram** — Create a bot via [@BotFather](https://t.me/botfather), enter the token and your chat ID
3. **Add restaurant targets** — Paste the restaurant URL, set party size, preferred dates, and rank your slot preferences
4. **Start monitoring** — Hit the Start button on the Dashboard

## How Booking Works

1. Bot wakes up at the configured "booking window open" time
2. Checks the restaurant calendar for available slots
3. Filters by your exact party size and preferred date range
4. Tries to book your #1 preference first, then #2, #3, etc.
5. On success: stops immediately, sends Telegram confirmation
6. On all slots taken: notifies you, keeps monitoring for cancellations

## Disclaimer

This tool automates interactions with Omakase.in, which may violate their Terms of Service. Use at your own risk. The author is not responsible for any account suspensions or other consequences.
