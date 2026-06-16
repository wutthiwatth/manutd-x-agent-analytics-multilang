# Man Utd X Analytics Service — Python

Analytics-only worker สำหรับอ่าน `tweets` ที่ puller ดึงมาไว้แล้ว แล้วสร้างสรุป/tag/tier analysis ลง `tweet_analyses`.

ตัวนี้ **ไม่มี X API / ไม่มี puller** ใช้แค่ MongoDB + OpenAI API.

## Flow

```text
Existing puller service
  ↓ writes
MongoDB.tweets
  ↓ read
manutd-x-analytics-service-python
  ↓ writes
MongoDB.tweet_analyses
```

## Environment

```bash
MONGO_URI=mongodb://YOUR_EXISTING_MONGO_HOST:27017
MONGO_DB_NAME=utd_x_agent
MONGO_COLLECTION_TWEETS=tweets
MONGO_COLLECTION_TWEET_ANALYSES=tweet_analyses

OPENAI_API_KEY=put_your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini
OPENAI_MAX_OUTPUT_TOKENS=4000

ANALYTICS_BATCH_SIZE=10
ANALYTICS_INTERVAL_MINUTES=10
ANALYTICS_RETRY_FAILED=true
```

## Run local once

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main --once
```

## Run local loop

```bash
python -m app.main
```

## Docker local

```bash
docker build -t manutd-x-analytics-python .
docker run --env-file .env manutd-x-analytics-python
```

## CapRover

Create app:

```text
manutd-x-analytics
```

Use this repo/zip with `captain-definition`. Do not enable public web access because this is a background worker.

## Output collection: tweet_analyses

```javascript
{
  tweet_id: "1234567890",
  tweet_url: "https://x.com/i/web/status/1234567890",
  author_x_username: "utdreport",

  tier_key: "aggregator",
  tier_name: "Aggregator",
  reliability_score: 40,

  summary_th: "สรุปภาษาไทยสั้น ๆ",
  summary_en: "Short English summary",

  category: "transfer",
  tags: ["transfer", "mufc", "striker"],
  tags_en: ["transfer", "mufc", "striker"],
  tags_th: ["ซื้อขาย", "แมนยู", "กองหน้า"],

  entities: {
    players: ["Benjamin Sesko"],
    clubs: ["Manchester United"],
    competitions: [],
    people: []
  },

  sentiment: "neutral",
  confidence: 0.82,
  importance_score: 70,
  final_score: 61,
  is_rumour: true,
  analyzed_at: ISODate("2026-06-16T12:01:00.000Z")
}
```

## Query examples

```javascript
use utd_x_agent

db.tweet_analyses.find().sort({ final_score: -1 }).limit(20)
db.tweet_analyses.find({ category: "transfer" }).sort({ final_score: -1 }).limit(20)
db.tweet_analyses.find({ tags_en: "injury" }).sort({ analyzed_at: -1 }).limit(20)
db.tweet_analyses.find({ tags_th: "บาดเจ็บ" }).sort({ analyzed_at: -1 }).limit(20)
```
