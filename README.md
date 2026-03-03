# 🆘 ResQ Backend — Setup & Run Guide

## Folder Structure

```
resq/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Environment variables + constants
│   ├── models.py                # Pydantic data models
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example             # Copy to .env and fill keys
│   ├── modules/
│   │   ├── gemini.py            # Gemini AI: classify, escalation, rumor, translate
│   │   ├── ingestion.py         # RSS feed ingestion background loop
│   │   ├── environmental.py     # Weather + river data APIs
│   │   ├── verification.py      # 4-layer rumor verification engine
│   │   ├── risk_engine.py       # UDRI + timeline predictor (all disaster types)
│   │   ├── notifier.py          # Email/SMS distress notifications
│   │   └── state.py             # Shared in-memory state
│   ├── routers/
│   │   ├── alerts.py            # GET /api/alerts, GET /api/alerts/{id}
│   │   ├── risk.py              # POST /api/risk/score, GET /api/risk/udri
│   │   ├── distress.py          # POST /api/distress/sos, /safety-check, /safe
│   │   ├── verify.py            # POST /api/verify
│   │   ├── translate.py         # POST /api/translate, /api/translate/batch
│   │   └── shelter.py           # GET /api/shelter/nearest
│   └── data/
│       └── survival_guide.json  # Offline survival guide (all disasters, 5 languages)
├── frontend/
│   └── resq-connected.html      # Existing UI connected to backend
└── docker-compose.yml
```

---

## 🚀 Quick Start (Local)

### 1. Clone and configure
```bash
cd resq/backend
cp .env.example .env
# Edit .env and add your keys
```

### 2. Get your API keys

**Note on models/quotas:**
The backend defaults to the `gemini-2.0-flash` model which is available to
everyone. If you have a paid or pro key you can override this by setting
`GEMINI_MODEL=gemini-2.0-pro` (or another supported model) in your `.env`.
The code now includes a short cooldown when the API returns a
`RESOURCE_EXHAUSTED` error so that ingest loops keep running even when you
run out of free quota.

| Key | Where to get |
|-----|-------------|
| `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey |
| `OPENWEATHER_API_KEY` | https://openweathermap.org/api (free tier) |
| `SMTP_USER` / `SMTP_PASS` | Gmail App Password |
| `TWILIO_*` | https://twilio.com (optional, for SMS) |

### 3. Install and run
```bash
cd resq/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Open frontend
Open `frontend/resq-connected.html` in your browser.
Set API URL to `http://localhost:8000` and click **Connect**.

---

## 🐳 Docker (Recommended)

```bash
cd resq
docker-compose up --build
```

API available at: `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs`

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/alerts/` | All active alerts (sorted by risk score) |
| GET | `/api/alerts/{id}` | Alert detail + action steps |
| POST | `/api/alerts/refresh` | Force re-compute from ingested data |
| GET | `/api/risk/udri` | Current area UDRI |
| POST | `/api/risk/score` | Personalised UDRI for user GPS |
| POST | `/api/distress/sos` | Trigger SOS → notify emergency contact |
| POST | `/api/distress/safety-check` | Start "Are You Safe?" loop |
| POST | `/api/distress/safe` | User confirms safety |
| POST | `/api/distress/check-loop` | Scheduler: check timed-out safety loops |
| POST | `/api/verify/` | Run 4-layer verification on a disaster claim |
| POST | `/api/translate/` | Translate text via Gemini |
| POST | `/api/translate/batch` | Translate multiple texts |
| GET | `/api/shelter/nearest` | Nearest open shelters by GPS |
| POST | `/api/chat` | Conversational safety assistant (location‑aware) |

---

## � Local & National News

The ingestion module pulls disaster news from both national and local sources.
By default it uses the GNews API with India‑focused queries; if no API key is
available an RSS fallback is used.  The RSS feeds list in
`modules/ingestion.py` already includes city feeds (Chennai, Kerala, other
states) but you can add additional URLs to the `FEEDS` list with `"local"`
as the second tuple element to treat them as local articles.

Each `NewsItem` returned by `/api/alerts` includes a `source_type` field that
is either `"national"` or `"local"` (or `"official"` when the source is
an agency).  Clients can filter accordingly.
**New!** you can also fetch raw news items directly via
`GET /api/alerts/news?lat=<lat>&lon=<lon>`.  Providing coordinates returns only
articles whose location lies within about 100 km of the user; omit the query
params to receive all ingested articles.  This makes it easy to show
newspaper headlines specific to the user's town without having to parse the
alerts themselves.
You are free to extend the query set or feed list to cover other languages or
regions – the classifier is language‑agnostic (it simply looks for keywords).


## 💬 Conversational Chatbot

A lightweight chat endpoint is available for personalized disaster advice. It
**prefers to call Gemini** for rich, conversational responses but will always
fall back to offline logic if the model is unavailable or out of quota.

The backend attempts to extract a city name from the user's message or the
`location` field; it also uses a small offline coordinate map to resolve
nearby towns. If the provided town is not in the database, you'll still get
**generic guidelines** and the name of your town is echoed in the reply.  For
example, asking about "Madurai" or "near Madurai" returns advice that begins
"In Madurai during FLOOD…" even though we don't have city‑specific data.

Responses can be translated.  The chat request now accepts a `language`
parameter (ISO code like `"hi"`, `"ta"`, `"en"`). If a non‑English language
is requested and a Gemini API key is configured the final answer is sent to
the `/api/translate` logic (via `modules.gemini.translate_text`) before being
returned.

You can see the implementation in `modules/location_intelligence.py` and
`routers/chat.py`.


## 🤖 How the AI Pipeline Works

```
RSS Feeds (every 5min)
       ↓
Keyword filter (is disaster-related?)
       ↓
Gemini: classify_disaster() → type, location, severity, escalation, credibility
       ↓
In-memory state (state.raw_articles)
       ↓
On /api/alerts request:
  ├── Group articles by (disaster_type, location)
  ├── get_weather() + get_river_data()
  ├── compute_weather_intensity() + compute_river_trend_score()
  ├── get_escalation_score() via Gemini NLP
  ├── verify_disaster() → 4-layer confidence score
  ├── compute_risk_score() → UDRI 0-100
  ├── predict_timeline_hours()
  └── Return sorted DisasterAlert list
```

---

## 📱 Flutter/React Native Integration

### Fetch alerts
```dart
final res = await http.get(
  Uri.parse('$API_BASE/api/alerts/?lat=$lat&lon=$lon&language=$lang')
);
final alerts = jsonDecode(res.body) as List;
```

### Trigger distress SOS
```dart
await http.post(
  Uri.parse('$API_BASE/api/distress/sos'),
  body: jsonEncode({
    'latitude': position.latitude,
    'longitude': position.longitude,
    'timestamp': DateTime.now().toIso8601String(),
    'battery_percent': batteryLevel,
    'disaster_type': activeAlert?.disasterType,
    'user_name': userName,
    'emergency_contact_phone': contactPhone,
    'emergency_contact_email': contactEmail,
    'language': selectedLang,
  }),
);
```

### Offline fallback
The `offline_sms` field in the `/api/distress/sos` response contains
a pre-built SMS string. Store it locally and use `telephony` package
to send directly when offline:
```dart
if (!isConnected) {
  await launchUrl(Uri.parse('sms:$emergencyPhone?body=$offlineSmsText'));
}
```

---

## 🗣 Supported Languages
- English (`en`)
- Hindi (`hi`)
- Tamil (`ta`)
- Telugu (`te`)
- Marathi (`mr`)

Static survival guides stored in `data/survival_guide.json`.
Dynamic content (alerts, risk explanations) translated via Gemini.

---

## ⚡ Production Considerations
- Replace in-memory `state.py` with **Redis**
- Replace mock river data with **CWC/WRIS API** (register at cwc.gov.in)
- Add **PostGIS** for accurate geo-proximity queries
- Add **Firebase** for push notifications to mobile
- Schedule `POST /api/distress/check-loop` with a cron job every minute
- Add rate limiting with `slowapi`
