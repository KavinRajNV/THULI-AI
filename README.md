# 🌾 KISAN.AI

**Multilingual voice-first agricultural intelligence for Tamil Nadu farmers.**

No smartphone. No internet. No app. Just a phone call.

---

## What is KISAN.AI?

Farmers call a phone number, speak in Tamil (or any language), and get instant agricultural **decisions** — not information. The system uses real dam data, live weather, soil analysis, and ML crop recommendations to give actionable advice.

### Key Features

- **Voice-first**: Works on basic button phones via Exotel IVR
- **Multilingual**: Auto-detects Tamil, English, Hindi, Telugu — responds in the same language
- **Real data**: Live dam levels scraped daily, 3-day weather forecasts, district soil data
- **Decisions not data**: "Don't irrigate today, rain coming tomorrow" instead of "78% rain chance"
- **Proactive alerts**: System calls farmers when dam releases or heavy rain predicted
- **Intent-based routing**: Only calls relevant services, keeping GPT costs minimal

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| Database | MongoDB Atlas (motor async) |
| AI | OpenAI GPT-4o-mini, Whisper-1, TTS-1 |
| Weather | WeatherAPI.com |
| Phone | Exotel webhooks |
| Frontend | React (Vite) + TailwindCSS |
| Scraping | BeautifulSoup4 (dam data) |
| ML | scikit-learn RandomForest (crop recommendation) |
| Scheduler | APScheduler |

---

## Quick Start

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy .env and fill in your API keys
cp .env.example .env

# Place your dataset files in backend/datasets/
# Place RandomForest.pkl in backend/datasets/models/

# Run
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 3. Environment Variables

Create `backend/.env`:

```
OPENAI_API_KEY=sk-...
MONGODB_URI=mongodb+srv://...
WEATHER_API_KEY=...
EXOTEL_SID=...
EXOTEL_TOKEN=...
EXOTEL_VIRTUAL_NUMBER=...
BASE_URL=https://your-domain.com
```

---

## Architecture

```
Phone Call → Exotel → Webhook → Whisper (STT)
                                    ↓
                            Intent Detection (zero cost)
                                    ↓
                        Service Routing (parallel)
                     ┌──────┬──────┬──────┬──────┐
                  Weather  Dam   Soil  Disease Fertilizer
                     └──────┴──────┴──────┴──────┘
                                    ↓
                         GPT-4o-mini (lean context)
                                    ↓
                              TTS-1 → Audio
                                    ↓
                            Exotel → Farmer hears response
```

---

## API Endpoints

### Chat
- `POST /api/chat/text` — Text chat (web UI)
- `POST /api/chat/voice` — Voice chat (web UI)
- `GET /api/farmer/{phone}` — Get farmer profile

### Exotel Webhooks
- `POST /exotel/incoming` — Handle incoming call
- `POST /exotel/process` — Process voice recording
- `POST /exotel/status` — Call status callback

### Admin
- `GET /api/admin/stats` — Dashboard statistics
- `GET /api/admin/farmers` — Farmer list (searchable)
- `GET /api/admin/farmer/{phone}/conversations` — Conversation history
- `GET /api/admin/dams` — Live dam status
- `GET /api/admin/alerts` — Alert log

### Alerts
- `POST /api/alerts/trigger` — Manually trigger alert
- `GET /api/alerts/check-conditions` — Check alert conditions

### Health
- `GET /ping` — Keep-alive for Render.com

---

## Datasets Required

Place these in `backend/datasets/`:

| File | Description |
|------|-------------|
| Villages.csv | 11,671 villages with pincode + district |
| Soil_data.csv | 875 rows of district soil NPK data |
| KrishnaGiri.csv | Krishnagiri district soil data |
| Dharmapuri.csv | Dharmapuri district soil data |
| Thanjvur_dataset.xlsx | Thanjavur district soil data |
| cropdata_updated.csv | 16,411 crop stage records |
| irrigation_prediction.csv | 10,000 irrigation need records |
| Yield-data.csv | 1,000 yield prediction records |
| plant_disease.csv | 113 disease symptom records |
| Crop_recommendation.csv | 2,200 crop recommendation records |
| tn_dam_irrigation_dataset.json | 14 dam → district mappings |
| reservoir_data_3years.csv | 6,576 historical reservoir records |
| models/RandomForest.pkl | Trained crop recommendation model |

---

## Deployment (Render.com)

1. Push to GitHub
2. Create Render Web Service → point to `backend/`
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables in Render dashboard
6. Deploy frontend as Render Static Site → point to `frontend/`, build: `npm run build`
7. Set up UptimeRobot to ping `/ping` every 10 minutes

---

## Cost Breakdown

- **OpenAI**: ~$5 covers entire hackathon (GPT-4o-mini + Whisper + TTS)
- **MongoDB Atlas**: Free tier (512MB)
- **WeatherAPI**: Free tier (1M calls/month)
- **Render.com**: Free tier
- **Exotel**: Pay per call (~₹1/min)

---

## License

Built for hackathon demonstration purposes.
