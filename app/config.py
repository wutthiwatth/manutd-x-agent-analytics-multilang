import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def required(name: str) -> str:
    value = os.getenv(name, '').strip()
    if not value:
        raise RuntimeError(f'Missing required env var: {name}')
    return value


def int_env(name: str, fallback: int) -> int:
    raw = os.getenv(name, '').strip()
    if not raw:
        return fallback
    try:
        value = int(raw)
        return value if value > 0 else fallback
    except ValueError:
        return fallback


def bool_env(name: str, fallback: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return fallback
    return raw.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


@dataclass(frozen=True)
class Config:
    mongo_uri: str
    mongo_db_name: str
    mongo_collection_tweets: str
    mongo_collection_tweet_analyses: str
    openai_api_key: str
    openai_model: str
    openai_max_output_tokens: int
    analytics_batch_size: int
    analytics_interval_minutes: int
    retry_failed: bool


config = Config(
    mongo_uri=required('MONGO_URI'),
    mongo_db_name=os.getenv('MONGO_DB_NAME', 'utd_x_agent').strip() or 'utd_x_agent',
    mongo_collection_tweets=os.getenv('MONGO_COLLECTION_TWEETS', 'tweets').strip() or 'tweets',
    mongo_collection_tweet_analyses=os.getenv('MONGO_COLLECTION_TWEET_ANALYSES', 'tweet_analyses').strip() or 'tweet_analyses',
    openai_api_key=required('OPENAI_API_KEY'),
    openai_model=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini').strip() or 'gpt-4.1-mini',
    openai_max_output_tokens=int_env('OPENAI_MAX_OUTPUT_TOKENS', 4000),
    analytics_batch_size=int_env('ANALYTICS_BATCH_SIZE', 10),
    analytics_interval_minutes=int_env('ANALYTICS_INTERVAL_MINUTES', 10),
    retry_failed=bool_env('ANALYTICS_RETRY_FAILED', True),
)
