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
MONGO_COLLECTION_ANALYTICS_STATE=analytics_state

OPENAI_API_KEY=put_your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini
OPENAI_MAX_OUTPUT_TOKENS=4000

ANALYTICS_BATCH_SIZE=10
ANALYTICS_INTERVAL_MINUTES=10
ANALYTICS_MAX_BATCHES_PER_CYCLE=0
ANALYTICS_SLEEP_BETWEEN_BATCHES_MS=500
ANALYTICS_PENDING_TIMEOUT_MINUTES=30
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

## Behavior

Service จะทำเป็น drain cycle:

```text
1. หา tweets ที่ยังไม่มี _analytics.status=done
2. เช็ก tweet_analyses ว่า tweet_id มีแล้วไหม
3. ถ้ามีแล้ว mark tweets._analytics.status=done โดยไม่ยิง OpenAI ซ้ำ
4. ถ้ายังไม่มี ส่งเข้า OpenAI เป็น batch
5. เขียน tweet_analyses
6. mark tweets._analytics.status=done
7. วน batch ถัดไปจนหมด
8. sleep ตาม ANALYTICS_INTERVAL_MINUTES
```

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
[analytics] Cycle done. batches=4 analyzed=40 pending=0
[analytics] Running drain cycle every 10 minute(s).
```

## Check state

```javascript
use utd_x_agent

db.analytics_state.findOne({ _id: "main" })
db.tweets.countDocuments({ "_analytics.status": "done" })
db.tweets.countDocuments({ "_analytics.status": "failed" })
db.tweet_analyses.countDocuments()
```
