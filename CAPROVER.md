# CapRover: Python Analytics-only Worker

Deploy แยกจาก puller:

```text
manutd-x-puller      -> รันตัวเดิม ดึง tweets เข้า Mongo
manutd-x-analytics   -> รันตัวนี้ วิเคราะห์ tweets ใน Mongo
```

> ตัว analytics ไม่มี X API token และไม่ดึง tweets เอง

## CapRover app

```text
App Name: manutd-x-analytics
Public access: off
HTTP/HTTPS: ไม่ต้องเปิด
```

## Env

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

ถ้า Mongo อยู่ใน CapRover app อื่น:

```bash
MONGO_URI=mongodb://srv-captain--your-mongo-app:27017
```

ถ้ามี auth:

```bash
MONGO_URI=mongodb://USER:PASSWORD@srv-captain--your-mongo-app:27017/admin?authSource=admin
```

หรือถ้า URI ระบุ database แล้วก็ยังแนะนำใส่ `MONGO_DB_NAME=utd_x_agent` ให้ชัดเจน

## Deploy

ใช้ `captain-definition` ที่ root:

```json
{
  "schemaVersion": 2,
  "dockerfilePath": "./Dockerfile"
}
```

Deploy ผ่าน UI หรือ CLI:

```bash
caprover deploy
```

## Logs

ควรเห็นประมาณนี้:

```text
[analytics] Analyzing 10 tweet(s)...
[analytics] Done. analyzed=10
[analytics] Running every 10 minute(s).
```

## Run one-off locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main --once
```
