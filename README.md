# I Ching Oracle ☰☷

An English-language I Ching (六爻) divination website for international users. Ask a question, cast three coins, and get an AI-powered reading.

## Features

- 🪙 **Coin Casting** — Interactive 3-coin toss animation (6 tosses build your hexagram)
- 🔮 **Free Preview** — Hexagram name, symbol, and judgment text at no cost
- 🤖 **Full Reading** — AI-generated in-depth interpretation (powered by DeepSeek)
- 📥 **Download Result** — Save your reading as an image
- 🔑 **No Account Needed** — One-time payment via Gumroad, no login, no subscriptions

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Single HTML page + Tailwind CSS |
| Backend | Python FastAPI (Railway) |
| AI | DeepSeek API |
| Payment | Gumroad (license key verification) |
| Hosting | Railway.app |

## Quick Start

### 1. Deploy on Railway

1. Fork/clone this repo to your GitHub
2. Go to [Railway.app](https://railway.app) → New Project → Deploy from GitHub repo
3. Add environment variables in Railway dashboard:
   - `DEEPSEEK_API_KEY` — Your DeepSeek API key
   - `GUMROAD_SECRET` — Your Gumroad webhook secret (optional)
4. Railway auto-deploys. Get your URL like `your-project.up.railway.app`

### 2. Set up Gumroad

1. Create a product on Gumroad (digital, $3.99, license key enabled)
2. Set product URL (e.g., `iching-oracle`)
3. Configure webhook in Gumroad → Settings → API → Webhook
   - URL: `https://your-project.up.railway.app/api/verify-payment`

### 3. Configure Domain (Optional)

- Railway provides a free `*.up.railway.app` subdomain
- For production, add a custom domain in Railway dashboard

## Project Structure

```
iching-oracle/
├── api/
│   └── divination.py      # FastAPI backend (6爻 engine + AI)
├── index.html              # Frontend (single page)
├── iching_data.json        # 64 hexagrams reference data
├── railway.json            # Railway deployment config
├── requirements.txt        # Python dependencies
└── README.md
```

## API Endpoints

- `GET /api/cast?question=...` — Cast hexagram, returns free preview
- `POST /api/full-reading` — Generate AI reading (after payment)
- `POST /api/verify-payment` — Verify Gumroad license key

## Cost

- **Railway**: Free tier ($5/mo credit, more than enough for MVP)
- **DeepSeek API**: ~$0.0005 per reading
- **Domain**: $0 (use Railway subdomain) or ~$10/yr for custom domain
- **Total**: ~$0/mo for MVP

## License

MIT
