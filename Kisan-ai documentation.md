# 🌾 KISAN.AI — Comprehensive Technical Documentation

> **Multilingual voice-first agricultural intelligence for Tamil Nadu farmers.**
> No smartphone. No internet. No app. Just a phone call.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Directory Structure](#4-directory-structure)
5. [Backend Deep Dive](#5-backend-deep-dive)
   - 5.1 [Application Entry Point (`main.py`)](#51-application-entry-point-mainpy)
   - 5.2 [Database Layer (`services/db.py`)](#52-database-layer-servicesdbpy)
   - 5.3 [Data Loader (`data/loader.py`)](#53-data-loader-dataloaderpy)
   - 5.4 [Service Layer](#54-service-layer)
   - 5.5 [Router Layer (API Endpoints)](#55-router-layer-api-endpoints)
   - 5.6 [Scheduler (`scheduler.py`)](#56-scheduler-schedulerpy)
   - 5.7 [Seed Script (`seed_demo.py`)](#57-seed-script-seed_demopy)
6. [Frontend Deep Dive](#6-frontend-deep-dive)
7. [Data Pipeline Flow](#7-data-pipeline-flow)
8. [Datasets Reference](#8-datasets-reference)
9. [API Reference](#9-api-reference)
10. [Environment Variables](#10-environment-variables)
11. [Deployment Guide](#11-deployment-guide)
12. [Cost Analysis](#12-cost-analysis)

---

## 1. Project Overview

KISAN.AI is an agricultural intelligence system designed for Tamil Nadu farmers who may not have smartphones or internet access. Farmers call a phone number, speak in Tamil (or English, Hindi, Telugu, Kannada, Malayalam), and receive **actionable agricultural decisions** — not raw data.

### Core Philosophy

- **Decisions, not information**: Instead of "78% rain chance", the system says "Don't irrigate today, rain coming tomorrow."
- **Voice-first**: Works on basic feature phones via Exotel IVR — no app installation required.
- **Real data**: Live dam levels scraped daily from `tnagriculture.in`, 3-day weather forecasts from WeatherAPI.com, district-level soil NPK data from CSV datasets.
- **Cost-minimal**: Intent detection is zero-cost (keyword-based). GPT-4o-mini is only called once per query with lean, pre-filtered context. Daily OpenAI cost ≈ $0.10–$0.50.

### What It Solves

| Problem | KISAN.AI Solution |
|---------|-------------------|
| Farmers can't read weather apps | Voice response in their language |
| No smartphone/internet | Works on any phone via IVR call |
| Generic farming advice | District-specific, crop-specific, stage-specific advice |
| No awareness of dam releases | Proactive phone alerts when dangerous outflows detected |
| Language barrier | Auto-detects Tamil/English/Hindi/Telugu and responds in same language |

---

## 2. System Architecture

### End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        FARMER INTERACTION                       │
│                                                                 │
│  📱 Phone Call ──► Exotel IVR ──► Webhook ──► Backend           │
│  💻 Web Browser ──────────────────────────► Backend             │
│  🎤 Voice Input ──► MediaRecorder ──────────► Backend           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       BACKEND PIPELINE                          │
│                                                                 │
│  ① Whisper-1 (STT) ──► Tamil/English text                      │
│  ② Onboarding Check ──► New farmer? Collect pincode/crop/days  │
│  ③ Intent Detection ──► Zero-cost keyword matching             │
│  ④ Parallel Data Fetch:                                        │
│     ├── Weather API (3-day forecast)                            │
│     ├── Dam Status (MongoDB / scraper)                          │
│     ├── Soil NPK (CSV dataset)                                 │
│     ├── Crop Stage (CSV dataset)                                │
│     ├── Disease Match (CSV + fuzzy)                             │
│     ├── Fertilizer Rules (NPK thresholds)                      │
│     └── Crop Recommendation (RandomForest / rules)             │
│  ⑤ GPT-4o-mini ──► Generate decision (max 200 tokens)          │
│  ⑥ TTS-1 Nova ──► Convert to speech (speed=0.85)               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RESPONSE DELIVERY                          │
│                                                                 │
│  📱 Exotel IVR ──► <Play> MP3 ──► Farmer hears response        │
│  💻 Web UI     ──► JSON + Audio URL ──► Text + audio playback   │
└─────────────────────────────────────────────────────────────────┘
```

### Scheduled Background Jobs

```
┌──────────────────────────────────────────────────────────────┐
│                    APScheduler CRON JOBS                      │
│                                                              │
│  06:00 AM ──► Scrape dam data from tnagriculture.in          │
│  07:00 AM ──► Check alert conditions (dam + weather)         │
│  02:00 AM ──► Cleanup static MP3 files older than 24 hours   │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend Framework** | FastAPI 0.111.0 (Python) | Async REST API with auto-generated Swagger docs |
| **Database** | MongoDB Atlas via `motor` 3.4.0 (async) | Farmer profiles, dam status, weather cache, alert logs |
| **AI — Chat** | OpenAI GPT-4o-mini | Generate agricultural decisions (max 200 tokens, temp=0) |
| **AI — STT** | OpenAI Whisper-1 | Transcribe Tamil/English voice to text |
| **AI — TTS** | OpenAI TTS-1 (voice: nova, speed: 0.85) | Convert text responses to speech |
| **Weather** | WeatherAPI.com | 3-day forecast (temperature, humidity, rainfall, rain chance) |
| **Telephony** | Exotel IVR | Incoming/outgoing calls via webhooks + XML responses |
| **Web Scraping** | BeautifulSoup4 + httpx | Daily dam data from `tnagriculture.in` |
| **ML Model** | scikit-learn RandomForest (pickle) | Crop recommendation from soil/weather features |
| **Data Processing** | pandas 2.2.2 + numpy 1.26.4 | Load and query CSV/Excel datasets |
| **Scheduler** | APScheduler 3.10.4 (AsyncIO) | Cron jobs for scraping, alerts, cleanup |
| **Frontend** | React 18 (Vite 5) + TailwindCSS 3.4 | Web chat UI + admin dashboard |
| **Icons** | lucide-react 0.383.0 | UI icons |
| **Routing** | react-router-dom 6.23 | Client-side navigation (admin/farmer views) |

---

## 4. Directory Structure

```
KISAN-AI/
├── .gitignore                          # Root gitignore
├── README.md                           # Quick-start README
├── DOCUMENTATION.md                    # This file
│
├── backend/
│   ├── .env                            # Environment variables (secrets)
│   ├── .gitignore                      # Backend-specific gitignore
│   ├── main.py                         # FastAPI app entry point
│   ├── scheduler.py                    # APScheduler cron jobs
│   ├── seed_demo.py                    # One-time demo data seeder
│   ├── requirements.txt                # Python dependencies (15 packages)
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py                   # Dataset loading into global DataFrames
│   │   └── district_centroids.json     # 38 TN district lat/lon coordinates
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chat.py                     # Web UI chat endpoints (text + voice)
│   │   ├── exotel.py                   # Exotel IVR webhook handlers
│   │   ├── admin.py                    # Admin dashboard API
│   │   └── alerts.py                   # Alert management + outbound calls
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── db.py                       # MongoDB connection + collections
│   │   ├── ai_service.py              # GPT-4o-mini + Whisper + TTS
│   │   ├── intent_service.py          # Zero-cost keyword intent detection
│   │   ├── pipeline_service.py        # Intent-driven parallel data gathering
│   │   ├── farmer_service.py          # Profile CRUD + onboarding flow
│   │   ├── location_service.py        # Pincode/village → district resolver
│   │   ├── weather_service.py         # WeatherAPI.com integration
│   │   ├── dam_service.py             # Dam data + scraper + trend analysis
│   │   ├── soil_service.py            # Soil NPK/pH by district
│   │   ├── crop_service.py            # Crop stage + irrigation + recommendation
│   │   ├── disease_service.py         # Disease symptom matching
│   │   └── fertilizer_service.py      # NPK-threshold fertilizer rules
│   │
│   ├── Dataset/                        # Agricultural datasets (CSV, JSON, PKL)
│   │   ├── Villages.csv                # 11,671 TN villages with pincode+district
│   │   ├── Soil data.csv              # 875 rows of district soil NPK
│   │   ├── KrishnaGiri.csv            # Krishnagiri district soil data
│   │   ├── Dharmapuri.csv             # Dharmapuri district soil data
│   │   ├── Thanjvur dataset.xlsx      # Thanjavur district soil data (Excel)
│   │   ├── cropdata_updated.csv       # 16,411 crop stage records
│   │   ├── irrigation_prediction.csv  # 10,000 irrigation need records
│   │   ├── Yield-data.csv             # 1,000 yield prediction records
│   │   ├── plant_disease.csv          # 113 disease symptom records
│   │   ├── Crop_recommendation.csv    # 2,200 crop recommendation records
│   │   ├── tn_dam_irrigation_dataset.json  # 14 dam→district mappings
│   │   ├── reservoir_data_3years.csv  # 6,576 historical reservoir records
│   │   ├── RandomForest.pkl           # Trained crop recommendation model
│   │   └── XGBoost.pkl                # Alternative ML model
│   │
│   └── static/                         # Generated TTS audio files (ephemeral)
│
├── frontend/
│   ├── .gitignore                      # Frontend-specific gitignore
│   ├── index.html                      # HTML entry point
│   ├── package.json                    # Node dependencies
│   ├── vite.config.js                  # Vite configuration
│   ├── tailwind.config.js             # TailwindCSS configuration
│   ├── postcss.config.js             # PostCSS configuration
│   │
│   └── src/
│       ├── main.jsx                    # React root mount
│       ├── App.jsx                     # Route layout + role selector + admin login
│       ├── index.css                   # Global styles + Tailwind imports
│       │
│       ├── pages/
│       │   ├── FarmerChat.jsx          # Chat interface (text + voice)
│       │   └── AdminPanel.jsx          # Admin dashboard (stats, dams, farmers, alerts)
│       │
│       └── components/
│           ├── ChatBubble.jsx          # Message bubble with audio playback
│           ├── VoiceButton.jsx         # Mic recording with audio level monitor
│           └── DamStatusCard.jsx       # Reservoir status card (unused in final UI)
│
└── venv/                               # Python virtual environment
```

---

## 5. Backend Deep Dive

### 5.1 Application Entry Point (`main.py`)

**File**: [`main.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/main.py)

The FastAPI application uses the **lifespan** pattern for startup/shutdown lifecycle management.

**Startup Sequence**:
1. `load_dotenv()` runs **before any other imports** (critical — services read `os.getenv()` at import time)
2. Verify `OPENAI_API_KEY` and `MONGODB_URI` are set
3. `load_all_datasets()` — loads all CSV/Excel/JSON/PKL files into memory
4. `start_scheduler()` — starts 3 APScheduler cron jobs
5. Mounts `/static` directory for TTS audio file serving

**Middleware**:
- CORS: Allows all origins (`*`), all methods, all headers — for frontend dev server compatibility

**Routers Registered**:
| Router | Tags | Prefix |
|--------|------|--------|
| `chat.router` | Chat | `/api/chat/*` |
| `exotel.router` | Exotel | `/exotel/*` |
| `admin.router` | Admin | `/api/admin/*` |
| `alerts.router` | Alerts | `/api/alerts/*` |

**Built-in Endpoints**:
- `GET /ping` — Returns `{"status": "alive", "timestamp": "..."}` (for UptimeRobot keep-alive on Render.com)
- `GET /` — Returns app info + link to `/docs` (Swagger UI)

---

### 5.2 Database Layer (`services/db.py`)

**File**: [`db.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/services/db.py)

Uses `motor` (async MongoDB driver) connecting to MongoDB Atlas.

**Database**: `kisan_ai`

**Collections**:

| Collection | Purpose | Key Fields |
|-----------|---------|------------|
| `farmers` | Farmer profiles + conversation history | `phone` (unique index), `district`, `primary_crop`, `days_after_sowing`, `onboarding_complete`, `conversation_history[]`, `language`, `channel` |
| `dam_status` | Daily dam/reservoir data (scraped or seeded) | `reservoir`, `date`, `storage_percentage`, `current_inflow_cusecs`, `current_outflow_cusecs`, `current_storage_mcft`, `full_capacity_mcft` |
| `weather_cache` | Cached weather responses (6-hour TTL) | `_id` (cache key), `data`, `cached_at` (TTL index: 21600s) |
| `alert_log` | Proactive alert history | `district`, `reservoir`, `reason`, `alert_type`, `message`, `triggered_at` |

**Indexes Created**:
- `farmers.phone` — unique index
- `dam_status.(date, reservoir)` — compound index for date+reservoir lookup
- `weather_cache.cached_at` — TTL index (auto-deletes after 6 hours)
- `alert_log.triggered_at` — for chronological sorting

---

### 5.3 Data Loader (`data/loader.py`)

**File**: [`loader.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/data/loader.py)

Loads **all 14 dataset files** into global Python variables at startup. Services access these via `data.loader.VARIABLE_NAME` (module reference pattern — ensures they always get the post-load data).

**Dataset Auto-Discovery**: The loader checks 7 candidate directory paths to find the datasets directory, picking the first one with ≥3 data files. This handles various project structures (`datasets/`, `Dataset/`, etc.).

**File Resolution**: Handles filename variants (spaces vs underscores, case differences) via `_find_file()` and `_safe_read_csv()`.

**Global Variables Loaded**:

| Variable | Source File | Type | Record Count |
|----------|-----------|------|-------------|
| `VILLAGES_DF` | `Villages.csv` | DataFrame | 11,671 rows |
| `SOIL_DF` | `Soil data.csv` | DataFrame | 875 rows |
| `KRISHNAGIRI_DF` | `KrishnaGiri.csv` | DataFrame | ~200 rows |
| `DHARMAPURI_DF` | `Dharmapuri.csv` (skip 2 header rows) | DataFrame | ~200 rows |
| `THANJAVUR_DF` | `Thanjvur dataset.xlsx` | DataFrame | ~200 rows |
| `CROPDATA_DF` | `cropdata_updated.csv` | DataFrame | 16,411 rows |
| `IRRIGATION_DF` | `irrigation_prediction.csv` | DataFrame | 10,000 rows |
| `YIELD_DF` | `Yield-data.csv` | DataFrame | 1,000 rows |
| `DISEASE_DF` | `plant_disease.csv` | DataFrame | 113 rows |
| `CROP_REC_DF` | `Crop_recommendation.csv` | DataFrame | 2,200 rows |
| `RESERVOIR_DF` | `reservoir_data_3years.csv` | DataFrame | 6,576 rows |
| `DAM_IRRIGATION_DATA` | `tn_dam_irrigation_dataset.json` | dict/list | 14 dam entries |
| `DISTRICT_CENTROIDS` | `district_centroids.json` | dict | 38 districts |
| `CROP_MODEL` | `RandomForest.pkl` | sklearn model | — |

---

### 5.4 Service Layer

#### 5.4.1 AI Service (`ai_service.py`)

**File**: [`ai_service.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/services/ai_service.py)

Central AI integration with three OpenAI endpoints.

**Rate Limiting**: Global counter with 500 calls/day limit, resets every 24 hours.

##### GPT-4o-mini (Chat Completion)

- **Model**: `gpt-4o-mini`
- **Max tokens**: 200
- **Temperature**: 0 (deterministic — no randomness)
- **Timeout**: 15 seconds

**System Prompt** — 7 strict rules:
1. **Language matching**: Detect farmer's language from `<question>`, reply in same language
2. **Stateless**: Treat every question as the first and only question (no memory)
3. **Data-grounded**: Only use values from `<data>` tags. Never invent numbers.
4. **Single topic**: Answer only the detected intent topic (irrigation ≠ fertilizer)
5. **Disease protocol**: Check DISEASE_MATCH → soil deficiency → ask ONE follow-up → best guess
6. **Tamil numbers**: Write numbers as Tamil words (ஐம்பது, not 50)
7. **Format**: Maximum 3 sentences. Give DECISIONS not information.

**User Message Construction** (`_build_user_message()`):
The message sent to GPT is structured with XML-like tags:
```
<farmer>district=Thanjavur, crop=rice, days=45, lang=tamil</farmer>
<intent>irrigation, dam</intent>
<data>
WEATHER: today temp=32C rain=0mm humidity=78% Partly cloudy | tomorrow rain_chance=85% rain=12mm ...
DAM: Mettur storage=44.6% inflow=772cusecs outflow=1003cusecs historical_avg=65.2% release_likely=true(high)
CROP_STAGE: Vegetative
IRRIGATION_MODEL: Stage: Vegetative. Irrigation need: High
</data>
<question>என் நெல் வயலுக்கு இன்று தண்ணீர் பாய்ச்சலாமா?</question>
```

Only relevant data sections are included based on detected intents. This keeps the GPT context lean and costs minimal.

##### Whisper-1 (Speech-to-Text)

- **Model**: `whisper-1`
- **Temperature**: 0
- **Language hint**: Mapped from user's language preference (`tamil` → `ta`, `english` → `en`, etc.)
- **Tamil prompt**: A vocabulary hint string with common agricultural Tamil words, dam names, and Tamil numerals to improve transcription accuracy
- **Supported formats**: WebM, MP4, MP3, WAV, OGG (mapped via `EXT_MAP`)
- **Process**: Audio bytes → temp file → Whisper API → text → cleanup temp file

##### TTS-1 (Text-to-Speech)

- **Model**: `tts-1`
- **Voice**: `nova` (clearest for non-English text)
- **Speed**: `0.85` (slightly slower for clarity with Tamil)
- **Input limit**: First 500 characters of text
- **Output**: Streamed to an MP3 file in `static/` directory

---

#### 5.4.2 Intent Service (`intent_service.py`)

**File**: [`intent_service.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/services/intent_service.py)

**Zero-cost** keyword-based intent detection. No API calls. Handles Tamil, English, and Tanglish keywords, plus Whisper misheard variants.

**Detected Intents**:

| Intent | Example Triggers (Tamil / English / Tanglish) |
|--------|----------------------------------------------|
| `irrigation` | தண்ணீர், நீர்ப்பாசனம், water, pump, borewell, thanni, paasanam |
| `disease` | நோய், பூச்சி, இலை மஞ்சள், yellow leaves, pest, spot, wilt |
| `fertilizer` | உரம், யூரியா, urea, npk, deficiency, uram |
| `crop_recommend` | என்ன பயிர், which crop, next crop, அடுத்த, போடலாம் |
| `dam` | அணை, மேட்டூர், dam, reservoir, mettur, vaigai, anai |
| `weather` | மழை, வானிலை, rain, forecast, temperature, mazhai |
| `yield` | விளைச்சல், harvest, profit, vilaichal |

**Routing Logic**:
- Pure weather question (`weather` only intent) → remapped to `general` (pipeline fetches weather for general queries)
- `irrigation` + dam keywords → both `irrigation` and `dam` intents included
- If no keywords match → defaults to `general`
- If multiple intents detected but `weather` is one of them → `weather` is removed (the other specific intents take priority)

---

#### 5.4.3 Pipeline Service (`pipeline_service.py`)

**File**: [`pipeline_service.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/services/pipeline_service.py)

The **orchestrator** that decides which services to call based on detected intents, runs them **in parallel**, and assembles the context dict for GPT.

**Data Gathering by Intent**:

| Intent | Services Called (parallel) |
|--------|--------------------------|
| `irrigation` | weather + dam + soil + irrigation_need + crop_stage |
| `dam` | dam only |
| `disease` | disease_match + soil + fertilizer |
| `fertilizer` | soil + fertilizer |
| `crop_recommend` | soil + weather (then ML model as 2nd step) |
| `general` | weather only |

**Parallelism**: Uses `asyncio.gather()` with `return_exceptions=True` and a **10-second timeout**. If any individual service fails, others still succeed. Crop recommendation (ML model) runs as a separate step with a 5-second timeout.

**Output**: A `context` dict like:
```python
{
    "intents": ["irrigation", "dam"],
    "weather": {"today": {...}, "tomorrow": {...}},
    "dam": {"dam_name": "Mettur", "storage_pct": 44.6, ...},
    "soil": {"N": 240, "P": 18, "K": 200, "pH": 7.2},
    "crop_stage": "Vegetative",
    "irrigation_need": "Stage: Vegetative. Irrigation need: High"
}
```

---

#### 5.4.4 Farmer Service (`farmer_service.py`)

**File**: [`farmer_service.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/services/farmer_service.py)

Handles farmer profile CRUD and the **3-step onboarding flow**.

**CRUD Operations**:
- `get_or_create_farmer(phone)` — Creates new farmer doc if not found (default: Tamil, onboarding incomplete)
- `update_farmer(phone, updates)` — Partial update via `$set`
- `save_conversation_turn(phone, role, content)` — Appends to `conversation_history[]` array (capped at last 10 turns via `$slice: -10`), updates `last_called`
- `reset_farmer(phone)` — Deletes farmer document entirely

**Onboarding Flow** (3 steps):

| Step | Question | What It Extracts | How |
|------|----------|------------------|-----|
| 1. Location | "உங்கள் பின்கோடு சொல்லுங்கள்" | `district`, `village`, `lat`, `lon`, `pincode` | `extract_pincode()` → 6-digit regex, `_text_to_pincode()` → Tamil spoken digits, `extract_district_name()` → direct match, then `resolve_location()` |
| 2. Crop | "என்ன பயிர் சாகுபடி?" | `primary_crop` | `_extract_crop()` → 60+ crop name mappings (Tamil + English + Tanglish + Whisper variants) |
| 3. Days | "நடவு எத்தனை நாள்?" | `days_after_sowing` → sets `onboarding_complete=True` | `_extract_days()` → `_text_to_number()` → 100+ Tamil/English numeral mappings |

**Tamil Number Parsing** (`_text_to_number()`):

The most complex part of this module. Handles:
- Direct digits: `"45"` → `45`
- Tamil formal: `"நாற்பத்தி ஐந்து"` → `45` (forty + five)
- Tamil colloquial: `"நாப்பத்தி அஞ்சு"` → `45`
- Tanglish: `"naarpathu anju"` → `45`
- English words: `"forty five"` → `45`
- Whisper misheard variants: `"சைபர்"` → `0` (misheard "zero")

Also handles spoken pincodes digit-by-digit: `"ஆறு ஒன்று மூன்று பூஜ்யம் பூஜ்யம் ஒன்று"` → `"613001"`

**Crop Mapping** (`CROP_MAP`): 60+ entries covering:
- Tamil crop names: நெல் → rice, கரும்பு → sugarcane
- English: paddy → rice, corn → maize
- Tanglish: nel → rice, karumbu → sugarcane
- Whisper misspellings: நில் → rice, நெல்லு → rice

---

#### 5.4.5 Location Service (`location_service.py`)

**File**: [`location_service.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/services/location_service.py)

Resolves farmer location from pincodes, village names, or district names to a standardized `{district, village, lat, lon}` result.

**Resolution Priority**:
1. **Pincode → Villages.csv**: Match 6-digit pincode against `Villages.csv` (11,671 rows)
2. **Village name → fuzzy match**: Uses `difflib.get_close_matches()` with cutoff=0.6 against all village names
3. **Pincode → External API**: Falls back to `api.postalpincode.in` if CSV lookup fails
4. **District → centroids**: Adds lat/lon from `district_centroids.json` (38 TN districts)

---

#### 5.4.6 Weather Service (`weather_service.py`)

**File**: [`weather_service.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/services/weather_service.py)

Fetches 3-day weather forecast from WeatherAPI.com.

**Query Priority**: District name preferred over lat/lon (e.g., `"Thanjavur,Tamil Nadu,India"`)

**Caching**: Results cached in MongoDB `weather_cache` collection with 6-hour TTL. Prevents redundant API calls for the same district within the same day.

**Response Format**:
```python
{
    "today": {"temp_c": 32.5, "humidity": 78, "rainfall_mm": 0, "chance_of_rain": 20, "condition": "Partly cloudy"},
    "tomorrow": {"temp_c": 31.0, "humidity": 85, "rainfall_mm": 12.4, "chance_of_rain": 85, "condition": "Heavy rain"},
    "day3": {"temp_c": 30.0, "humidity": 80, "rainfall_mm": 5.0, "chance_of_rain": 60, "condition": "Light rain"}
}
```

---

#### 5.4.7 Dam Service (`dam_service.py`)

**File**: [`dam_service.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/services/dam_service.py)

Manages Tamil Nadu reservoir data with three capabilities: **direct lookup**, **district mapping**, and **web scraping**.

**Dam Name Extraction**: Recognizes 7 major dams in Tamil, English, and Tanglish:
- Mettur (மேட்டூர்), Bhavanisagar (பவானிசாகர் / பவானி), Amaravathi (அமராவதி), Vaigai (வைகை), Papanasam (பாப்பநாசம்), Manimuthar (மணிமுத்தாறு), Krishnagiri (கிருஷ்ணகிரி)

**Data Retrieval Priority** (`get_dam_context()`):
1. **Direct name in text**: If farmer says "மேட்டூர் அணை நிலவரம்?", directly fetch Mettur
2. **District mapping**: If no specific dam named, look up which dam serves the farmer's district via `tn_dam_irrigation_dataset.json` (dam → beneficiary_districts mapping)
3. **Fallback**: Return what's known or "no data" message

**Historical Trend Analysis** (`analyze_dam_trend()`):
- Filters `reservoir_data_3years.csv` for the specific dam and current month
- Calculates: historical average storage %, whether release is likely (avg outflow > 500 cusecs), confidence level (high/medium/low based on record count)

**Web Scraper** (`scrape_dam_data()`):
- Scrapes `https://tnagriculture.in/ARS/home/reservoir/{date}` daily at 6 AM
- Parses HTML table with BeautifulSoup
- Extracts: reservoir name, capacity, current storage, inflow, outflow, storage percentage
- Upserts into MongoDB `dam_status` collection

---

#### 5.4.8 Soil Service (`soil_service.py`)

**File**: [`soil_service.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/services/soil_service.py)

Returns district-level soil NPK, pH, organic carbon, and texture data.

**Data Source Priority**:
1. **District-specific file** (Krishnagiri, Thanjavur, Dharmapuri) → dedicated CSV/Excel with detailed data
2. **Generic soil data** (`Soil data.csv`) → filters by district column
3. **State average** → if no district match, averages all 875 rows
4. **Hardcoded defaults** → `{N: 240, P: 18, K: 200, pH: 7.2, OC: 0.5, texture: "Clay Loam"}`

**Output**:
```python
{"N": 240.0, "P": 18.5, "K": 195.0, "pH": 7.1, "OC": 0.55, "texture": "Clay Loam"}
```

---

#### 5.4.9 Crop Service (`crop_service.py`)

**File**: [`crop_service.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/services/crop_service.py)

Three functions: crop stage identification, irrigation need assessment, and crop recommendation.

##### `get_crop_stage(crop, days)` → String
Looks up the crop's growth stage from `cropdata_updated.csv` by finding the closest matching day count. Falls back to a simple estimate:
- ≤15 days → Germination
- ≤45 days → Vegetative
- ≤90 days → Flowering
- >90 days → Harvest

##### `get_irrigation_need(crop, days, district)` → String
Combines crop stage with `irrigation_prediction.csv` data. Filters by crop type and growth stage, returns the modal irrigation need value.

##### `recommend_crop(district, weather)` → String

**Two-tier approach**:

1. **ML Model (primary)**: `RandomForest.pkl` trained on `Crop_recommendation.csv`
   - Features: `[N, P, K, temperature, humidity, pH, rainfall]`
   - Input values clamped to training ranges to prevent out-of-distribution errors
   - If model crashes (e.g., version mismatch), falls back to rules

2. **Rule-Based (fallback)**:
   - District-specific crop lists for 10 major TN districts (e.g., Thanjavur → rice, blackgram, sesame)
   - Soil-based logic: low N → legumes, high rainfall → rice/sugarcane, acidic pH → rice/groundnut
   - Returns top 3 crops with reasoning

---

#### 5.4.10 Disease Service (`disease_service.py`)

**File**: [`disease_service.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/services/disease_service.py)

Matches farmer-reported symptoms against 113 known plant diseases.

**Tamil→English Translation**: 22 symptom translations (e.g., மஞ்சள் → "yellow yellowing", பூச்சி → "pest insect", வாடல் → "wilt wilting") expand the search space.

**Matching Algorithm**:
1. Translate Tamil symptoms to English equivalents
2. Filter by crop if known (e.g., only show rice diseases for rice farmers)
3. Tokenize expanded text, remove stop words
4. Score each disease by counting overlapping tokens with symptoms + disease name + causes columns
5. Return top 2 matches with disease name, crop, treatment, prevention, and match score

---

#### 5.4.11 Fertilizer Service (`fertilizer_service.py`)

**File**: [`fertilizer_service.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/services/fertilizer_service.py)

**Pure rule-based** (no ML model). Uses NPK deficiency thresholds to recommend specific fertilizers.

**Threshold Classification** (kg/ha):

| Nutrient | Low | Medium | High |
|----------|-----|--------|------|
| Nitrogen (N) | < 280 | 280–560 | > 560 |
| Phosphorus (P) | < 10 | 10–25 | > 25 |
| Potassium (K) | < 108 | 108–280 | > 280 |

**Recommendation Rules**:

| Condition | Fertilizer | Dose | Timing |
|-----------|-----------|------|--------|
| N low | Urea | 50 kg/acre | Split: 50% basal + 50% top dress at 30 days |
| N medium | Urea | 25 kg/acre | Top dress at 25–30 days |
| P low | SSP | 50 kg/acre | Basal before sowing |
| P medium | DAP | 25 kg/acre | Basal |
| K low | MOP | 25 kg/acre | Basal |
| K medium | MOP | 15 kg/acre | Basal |
| All balanced | NPK 17:17:17 | 25 kg/acre | Basal |

**Crop-specific notes** added for rice (zinc sulphate), cotton (boron spray), sugarcane (3-dose split), groundnut (gypsum at pegging), maize (3-dose N split).

**Priority**: N > P > K. Primary deficiency gets the main recommendation. Secondary deficiency noted if multiple deficiencies exist.

---

### 5.5 Router Layer (API Endpoints)

#### 5.5.1 Chat Router (`routers/chat.py`)

**File**: [`chat.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/routers/chat.py)

Web UI endpoints with fault-tolerant TTS.

##### `POST /api/chat/text`
**Body**: `{ "phone": "web_demo", "message": "...", "language": "tamil" }`

Flow:
1. Get or create farmer profile
2. Update language preference if changed
3. If onboarding incomplete → run `get_onboarding_response()`
4. If onboarding complete → `build_context()` → `get_kisan_response()`
5. Save both farmer and kisan turns to conversation history
6. Generate TTS audio (10s timeout, failure returns `null` — never blocks response)

**Response**: `{ "response_text": "...", "audio_url": "http://.../static/abc.mp3", "farmer_profile": {...} }`

##### `POST /api/chat/voice`
**Form data**: `audio` (UploadFile), `phone` (string), `language` (string)

Flow:
1. Read audio bytes (reject if < 500 bytes)
2. Transcribe with Whisper-1
3. Same pipeline as text chat (onboarding or full pipeline)
4. Save conversation + generate TTS

**Response**: Same as text + `"transcript": "..."` field

##### `POST /api/chat/reset`
Deletes farmer profile entirely. Used for "New Chat" in web UI.

##### `GET /api/farmer/{phone}`
Returns full farmer profile document (minus `_id`).

---

#### 5.5.2 Exotel Router (`routers/exotel.py`)

**File**: [`exotel.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/routers/exotel.py)

Handles the Exotel IVR phone call flow using XML-based TwiML responses.

##### `POST /exotel/incoming`
Triggered when a farmer calls the Exotel virtual number.

**New farmer** → Tamil greeting asking for pincode:
```xml
<Response>
  <Say voice="female" language="ta-IN">வணக்கம்! நான் KISAN AI. உங்கள் பின்கோடு சொல்லுங்கள்.</Say>
  <Record action="{BASE_URL}/exotel/process" maxLength="30" finishOnKey="#" playBeep="true"/>
</Response>
```

**Returning farmer** → Personalized greeting with their crop name:
```xml
<Response>
  <Say>வணக்கம்! உங்கள் rice பயிருக்கு இன்று என்ன கேள்வி?</Say>
  <Record .../>
</Response>
```

##### `POST /exotel/process`
Processes the voice recording from Exotel:

1. Guard: reject recordings < 2 seconds
2. Download audio from Exotel's `RecordingUrl` (authenticated with API_KEY:API_TOKEN)
3. Transcribe with Whisper → run onboarding or pipeline → generate TTS
4. Play response audio + record next question (loop):
```xml
<Response>
  <Play>{BASE_URL}/static/{CallSid}.mp3</Play>
  <Record action="{BASE_URL}/exotel/process" .../>
</Response>
```
5. Schedule MP3 file cleanup after 5 minutes (background task)

**Error handling**: On any failure, responds with Tamil apology and re-records.

##### `POST /exotel/status`
Call completion callback. Cleans up the associated MP3 file.

---

#### 5.5.3 Admin Router (`routers/admin.py`)

**File**: [`admin.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/routers/admin.py)

Dashboard statistics and data access for the admin panel.

##### `GET /api/admin/stats`
Returns aggregated statistics with demo-safe minimums:
```json
{
    "total_farmers": 43,       // max(actual, 43) — ensures demo looks populated
    "calls_today": 7,          // max(actual, 7)
    "active_districts": 8,     // max(distinct_districts, 8)
    "alerts_today": 2          // max(alert_count, 2)
}
```

##### `GET /api/admin/farmers?skip=0&limit=50&search=Thanjavur`
Paginated farmer list. Search across phone, district, and crop fields. Excludes `conversation_history` for performance. Sorted by `last_called` descending.

##### `GET /api/admin/farmer/{phone}/conversations`
Returns the full conversation history array for a specific farmer.

##### `GET /api/admin/dams`
Returns the latest dam data (most recent date). De-duplicates by reservoir name.

##### `GET /api/admin/alerts?limit=50`
Returns alert log sorted by `triggered_at` descending.

---

#### 5.5.4 Alerts Router (`routers/alerts.py`)

**File**: [`alerts.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/routers/alerts.py)

Proactive alert management — both manual triggers and automated condition checks.

##### `POST /api/alerts/trigger`
**Body**: `{ "district": "Thanjavur", "message": "...", "alert_type": "manual" }`

1. Finds all farmers in the specified district
2. For each farmer: generates TTS audio → makes Exotel outbound call → plays alert audio
3. Logs the alert with farmer count

**Outbound Call Flow**:
```
TTS-1 → MP3 file → Exotel API → Call farmer → Callback to /exotel/alert-play → <Play> MP3
```

##### `GET /api/alerts/check-conditions`
Scans current dam data for alert-worthy conditions:
- Storage < 20% → `low_storage` warning
- Outflow > 5,000 cusecs → `high_outflow` alert

Returns potential alerts for admin review (doesn't auto-trigger).

---

### 5.6 Scheduler (`scheduler.py`)

**File**: [`scheduler.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/scheduler.py)

Three AsyncIOScheduler cron jobs:

| Time | Job | Details |
|------|-----|---------|
| **06:00 AM** | `daily_dam_scrape` | Scrapes dam data from `tnagriculture.in`. Calls `dam_service.scrape_dam_data()` |
| **07:00 AM** | `daily_alert_check` | Checks 4 conditions for all dams + active districts: ① Dam outflow > 2× historical average ② Storage dropped > 15% in 24h ③ Storage < 20% ④ Rainfall > 80mm predicted tomorrow. Auto-creates alerts in MongoDB. |
| **02:00 AM** | `cleanup_static_files` | Deletes all files in `static/` older than 24 hours (orphaned TTS audio) |

**Alert Check Weather Loop**: Aggregates all districts with active (onboarded) farmers, fetches weather forecast for each using district centroids, triggers weather alert if tomorrow's rainfall exceeds 80mm.

---

### 5.7 Seed Script (`seed_demo.py`)

**File**: [`seed_demo.py`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/backend/seed_demo.py)

One-time script (`python seed_demo.py`) that populates MongoDB with realistic demo data. Safe to re-run — checks for `DEMO_SEED_V2` marker in `system_flags` collection.

**Seeds**:
- **7 dam records** with realistic June 13 data (Mettur, Bhavanisagar, Amaravathi, Vaigai, Papanasam, Manimuthar, Krishnagiri)
- **15 farmer profiles** across 13 TN districts with Tamil conversation history (10 onboarded, 2 partially onboarded, 3 with various crops)
- **2 alert records** (Papanasam high inflow, Mettur outflow)

---

## 6. Frontend Deep Dive

### 6.1 Application Structure

**Entry**: [`App.jsx`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/frontend/src/App.jsx) — Role-based routing with 3 screens before reaching the app:

```
RoleSelector → [Farmer] → FarmerChat
            → [Admin]  → AdminLogin → AdminNav + (AdminPanel | FarmerChat)
```

**Admin Credentials** (hardcoded for demo): `admin@gmail.com` / `Admin123`

### 6.2 FarmerChat Page

**File**: [`FarmerChat.jsx`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/frontend/src/pages/FarmerChat.jsx)

**Pre-chat flow**:
1. **Language selection** — 6 languages: Tamil (தமிழ்), English, Hindi (हिन्दी), Telugu (తెలుగు), Kannada (ಕನ್ನಡ), Malayalam (മലയാളം). Each has its own greeting message.
2. **Phone entry** — Optional for demo mode. If blank, generates `session_{timestamp}`.
3. **Greeting** — System message in chosen language asking for pincode.

**Chat interface**:
- Text input with send button
- Voice recording via `VoiceButton` component
- Auto-scroll to latest message
- Loading animation (bouncing dots)
- Profile sidebar (desktop only): shows language, district, crop, days, onboarding status
- "New Chat" button resets both frontend state and backend farmer record

### 6.3 AdminPanel Page

**File**: [`AdminPanel.jsx`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/frontend/src/pages/AdminPanel.jsx)

**Sections**:
1. **Stats Cards** — 4 metric cards: Total Farmers, Interactions Today, Districts Active, Alerts Issued
2. **Reservoir Status** — Color-coded dam cards (red < 20%, amber < 40%, blue < 70%, green ≥ 70%) with storage bar, inflow/outflow, capacity
3. **Registered Farmers** — Searchable table with channel (Phone/Web), phone, district, crop, status tabs. Click a farmer to view their conversation history.
4. **Conversation Log** — Shows selected farmer's chat history with timestamps
5. **Proactive Alerts** — Alert log with type, message, district, and timestamp

### 6.4 VoiceButton Component

**File**: [`VoiceButton.jsx`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/frontend/src/components/VoiceButton.jsx)

Sophisticated voice recording component with real-time audio monitoring:

1. **Start**: Requests microphone with minimal constraints (max browser compatibility)
2. **Audio level monitor**: Uses Web Audio API (`AudioContext` + `AnalyserNode`) to show real-time volume bar
3. **Recording**: Uses `MediaRecorder` with no mimeType constraint (browser chooses best format)
4. **Minimum duration**: Enforces 2-second minimum recording
5. **Stop**: Requests final data → creates Blob → sends to `/api/chat/voice` as multipart form
6. **Auto-play**: Plays TTS response audio automatically after receiving backend response

**Error Handling**: Handles NotAllowedError (permission denied), NotFoundError (no mic), small blob (< 2KB), empty chunks, and API errors — all with Tamil error messages.

### 6.5 ChatBubble Component

**File**: [`ChatBubble.jsx`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/frontend/src/components/ChatBubble.jsx)

- Farmer messages: Green bubble (right-aligned), white text
- KISAN AI messages: White bubble (left-aligned) with avatar, optional "Play audio" button

---

## 7. Data Pipeline Flow

### Complete Request Lifecycle (Text Chat)

```
1. User sends: "என் நெல் வயலுக்கு இன்று தண்ணீர் பாய்ச்சலாமா?"
   └─► POST /api/chat/text

2. get_or_create_farmer("web_demo")
   └─► MongoDB: find or insert farmer doc

3. Onboarding check: farmer.onboarding_complete == True
   └─► Skip onboarding, proceed to pipeline

4. detect_intents("என் நெல் வயலுக்கு இன்று தண்ணீர் பாய்ச்சலாமா?")
   └─► Keywords: "தண்ணீர்" → irrigation, "பாய்ச்ச" → irrigation
   └─► Result: ["irrigation"]

5. build_context() with intents=["irrigation"]:
   ├── weather_service.get_weather(district="Thanjavur")     → WeatherAPI → cache
   ├── dam_service.get_dam_context(district="Thanjavur")     → MongoDB dam_status
   ├── soil_service.get_soil_data("Thanjavur")               → Thanjavur_dataset.xlsx
   ├── crop_service.get_irrigation_need("rice", 45, "Thanjavur") → irrigation_prediction.csv
   └── crop_service.get_crop_stage("rice", 45)               → cropdata_updated.csv
   All run in PARALLEL with 10s timeout.

6. _build_user_message() assembles:
   <farmer>district=Thanjavur, crop=rice, days=45, lang=tamil</farmer>
   <intent>irrigation</intent>
   <data>
   WEATHER: today temp=32C rain=0mm humidity=78% | tomorrow rain_chance=85% rain=12mm
   DAM: Mettur storage=44.6% inflow=772cusecs outflow=1003cusecs
   CROP_STAGE: Vegetative
   IRRIGATION_MODEL: Stage: Vegetative. Irrigation need: High
   SOIL: N=240kg/ha P=18kg/ha K=200kg/ha pH=7.1
   </data>
   <question>என் நெல் வயலுக்கு இன்று தண்ணீர் பாய்ச்சலாமா?</question>

7. GPT-4o-mini generates (max 200 tokens, temp=0):
   "நாளை மழை வாய்ப்பு உள்ளது. இன்று நீர்ப்பாசனம் செய்ய வேண்டாம்.
    மேட்டூர் அணையில் நாற்பத்தி நான்கு சதவீதம் நீர் உள்ளது."

8. save_conversation_turn() × 2 (farmer + kisan)

9. text_to_speech() → static/abc123.mp3

10. Response JSON:
    {
      "response_text": "நாளை மழை வாய்ப்பு உள்ளது...",
      "audio_url": "http://localhost:8000/static/abc123.mp3",
      "farmer_profile": {"district": "Thanjavur", "crop": "rice", "days": 45, ...}
    }
```

### Complete Phone Call Lifecycle (Exotel)

```
1. Farmer dials Exotel number (+91XXXXXXXXXX)

2. Exotel POSTs to /exotel/incoming
   ├── From: +919944523601
   └── Backend returns XML: <Say> greeting + <Record>

3. Farmer speaks for up to 30 seconds, presses # or waits

4. Exotel POSTs to /exotel/process
   ├── RecordingUrl: https://exotel.com/recordings/xxx.mp3
   ├── From: +919944523601
   └── RecordingDuration: 8

5. Backend downloads audio from Exotel (Basic Auth)
   └── httpx.get(RecordingUrl, auth=(API_KEY, API_TOKEN))

6. Whisper-1 transcription (with Tamil vocabulary hint)
   └── "என் நெல் வயலுக்கு இன்று தண்ணீர் பாய்ச்சலாமா?"

7. Pipeline execution (same as text flow steps 4-7)

8. TTS-1 generates response MP3
   └── static/{CallSid}.mp3

9. XML response to Exotel:
   <Response>
     <Play>{BASE_URL}/static/{CallSid}.mp3</Play>
     <Record action="{BASE_URL}/exotel/process" .../>
   </Response>

10. Farmer hears response → can ask another question (loop)

11. Call ends → /exotel/status cleans up MP3
```

---

## 8. Datasets Reference

### Villages.csv (11,671 rows)
**Purpose**: Pincode → district + village resolver. Core of the onboarding location step.

| Column | Example |
|--------|---------|
| Village Name | Orathanadu |
| District | Thanjavur |
| Pincode | 614625 |

### Soil data.csv (875 rows)
**Purpose**: District-level soil nutrient data for all TN districts.

| Column | Example | Unit |
|--------|---------|------|
| District | Thanjavur | — |
| N | 240 | kg/ha |
| P | 18 | kg/ha |
| K | 200 | kg/ha |
| pH | 7.2 | — |
| OC | 0.55 | % |
| TexturalClass | Clay Loam | — |

### KrishnaGiri.csv, Dharmapuri.csv, Thanjvur dataset.xlsx
**Purpose**: High-resolution district-specific soil data with more samples and variables than the generic soil file.

### cropdata_updated.csv (16,411 rows)
**Purpose**: Maps crop type + days after sowing → growth stage (Germination, Vegetative, Flowering, Harvest).

### irrigation_prediction.csv (10,000 rows)
**Purpose**: Maps crop type + growth stage → irrigation need level (Low, Medium, High).

### Yield-data.csv (1,000 rows)
**Purpose**: Yield prediction data by crop, district, and season.

### plant_disease.csv (113 rows)
**Purpose**: Disease symptom → diagnosis + treatment database.

| Column | Example |
|--------|---------|
| Affected_Crop | Rice |
| Symptoms | Yellow leaves, stunted growth |
| Diseases | Nitrogen Deficiency |
| Treatment | Apply Urea 50 kg/acre |
| Prevention | Regular soil testing |
| Causes | Low N in soil |

### Crop_recommendation.csv (2,200 rows)
**Purpose**: Training data for RandomForest model. Features: N, P, K, temperature, humidity, pH, rainfall → label (crop name).

### tn_dam_irrigation_dataset.json (14 entries)
**Purpose**: Maps each dam to its beneficiary districts and canal systems. Used by `dam_service` for district → dam lookup.

### reservoir_data_3years.csv (6,576 rows)
**Purpose**: 3 years of daily reservoir data for historical trend analysis. Columns include date, reservoir, storage, inflow, outflow.

### RandomForest.pkl
**Purpose**: Pre-trained scikit-learn RandomForest model for crop recommendation. Input: 7 features `[N, P, K, temp, humidity, pH, rainfall]`. Output: crop label.

### district_centroids.json (38 entries)
**Purpose**: GPS coordinates (lat, lon) for all 38 Tamil Nadu districts. Used by weather service and alert system.

---

## 9. API Reference

### Chat Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/chat/text` | None | Send text message, get AI response + audio |
| `POST` | `/api/chat/voice` | None | Send voice recording, get transcription + AI response + audio |
| `POST` | `/api/chat/reset` | None | Delete farmer profile and start fresh |
| `GET` | `/api/farmer/{phone}` | None | Get full farmer profile |

### Exotel Webhook Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/exotel/incoming` | Exotel | Handle incoming call — greet + record |
| `POST` | `/exotel/process` | Exotel | Process voice recording — transcribe + respond |
| `POST` | `/exotel/status` | Exotel | Call status callback — cleanup |
| `POST` | `/exotel/alert-play` | Exotel | Play alert audio during outbound call |

### Admin Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/admin/stats` | None | Dashboard statistics |
| `GET` | `/api/admin/farmers` | None | Paginated, searchable farmer list |
| `GET` | `/api/admin/farmer/{phone}/conversations` | None | Farmer conversation history |
| `GET` | `/api/admin/dams` | None | Latest reservoir status for all dams |
| `GET` | `/api/admin/alerts` | None | Alert log (most recent first) |

### Alert Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/alerts/trigger` | None | Manually trigger alert for a district |
| `GET` | `/api/alerts/check-conditions` | None | Scan current conditions for potential alerts |

### Utility Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/ping` | Keep-alive for Render.com (UptimeRobot) |
| `GET` | `/` | App info + version |
| `GET` | `/docs` | Auto-generated Swagger UI |

---

## 10. Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `OPENAI_API_KEY` | ✅ | OpenAI API key for GPT, Whisper, TTS | `sk-proj-...` |
| `MONGODB_URI` | ✅ | MongoDB Atlas connection string | `mongodb+srv://user:pass@cluster.mongodb.net` |
| `WEATHER_API_KEY` | ✅ | WeatherAPI.com API key | `abc123def456` |
| `EXOTEL_SID` | ⚠️ Phone only | Exotel Account SID | `exotel_sid` |
| `EXOTEL_API_KEY` | ⚠️ Phone only | Exotel API key (Basic Auth username) | `api_key` |
| `EXOTEL_API_TOKEN` | ⚠️ Phone only | Exotel API token (Basic Auth password) | `api_token` |
| `EXOTEL_VIRTUAL_NUMBER` | ⚠️ Phone only | Exotel phone number farmers call | `+91XXXXXXXXXX` |
| `BASE_URL` | ✅ | Public URL of the backend server | `https://kisan-ai.onrender.com` |
| `PORT` | Optional | Server port (default: 8000) | `8000` |

> ⚠️ Exotel variables only needed for phone call functionality. Web chat works without them.

---

## 11. Deployment Guide

### Backend (Render.com)

1. Push code to GitHub
2. Create a **Web Service** on Render → point to `backend/` directory
3. **Build command**: `pip install -r requirements.txt`
4. **Start command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add all environment variables in the Render dashboard
6. **Keep-alive**: Set up UptimeRobot to ping `https://your-app.onrender.com/ping` every 10 minutes (Render free tier sleeps after 15 min inactivity)

### Frontend (Render Static Site)

1. Create a **Static Site** on Render → point to `frontend/` directory
2. **Build command**: `npm install && npm run build`
3. **Publish directory**: `dist`
4. Set `VITE_API_URL` environment variable to your backend URL

### Local Development

```bash
# Backend
cd backend
python -m venv venv
.\venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env            # Fill in API keys
python seed_demo.py             # One-time: seed demo data
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                     # Starts on http://localhost:5173
```

---

## 12. Cost Analysis

| Service | Pricing | Estimated Monthly Cost |
|---------|---------|----------------------|
| **OpenAI GPT-4o-mini** | $0.15/1M input, $0.60/1M output | ~$2–5 (200 tokens/query, 1000 queries/month) |
| **OpenAI Whisper-1** | $0.006/minute | ~$0.50 (500 calls × 6s avg) |
| **OpenAI TTS-1** | $15/1M chars | ~$2 (500 responses × 200 chars avg) |
| **MongoDB Atlas** | Free tier (512MB) | $0 |
| **WeatherAPI.com** | Free tier (1M calls/month) | $0 |
| **Render.com** | Free tier (with sleep) | $0 |
| **Exotel** | ~₹1/minute | ₹500–1000 for active usage |

**Total estimated cost**: ~$5–10/month for moderate usage (under 1,000 queries/month).

---

> **Document generated**: September 14, 2026
> **Project**: KISAN.AI — SIH 2026
> **Version**: 1.0.0
