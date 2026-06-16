from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.collection import Collection
from .config import config

_client: MongoClient | None = None
_db: Database | None = None


def get_db() -> Database:
    global _client, _db
    if _db is not None:
        return _db

    _client = MongoClient(config.mongo_uri, appname='manutd-x-analytics-service-python')
    _db = _client[config.mongo_db_name]
    ensure_indexes(_db)
    return _db


def get_tweets_collection() -> Collection:
    return get_db()[config.mongo_collection_tweets]


def get_tweet_analyses_collection() -> Collection:
    return get_db()[config.mongo_collection_tweet_analyses]


def ensure_indexes(db: Database) -> None:
    tweets = db[config.mongo_collection_tweets]
    tweets.create_index([('_analytics.status', ASCENDING)], name='idx_tweets_analytics_status')
    tweets.create_index([('created_at', DESCENDING)], name='idx_tweets_created_at_desc')

    analyses = db[config.mongo_collection_tweet_analyses]
    analyses.create_index([('tweet_id', ASCENDING)], unique=True, name='uniq_analysis_tweet_id')
    analyses.create_index([('analyzed_at', DESCENDING)], name='idx_analysis_analyzed_at_desc')
    analyses.create_index([('category', ASCENDING)], name='idx_analysis_category')
    analyses.create_index([('tags', ASCENDING)], name='idx_analysis_tags')
    analyses.create_index([('tags_en', ASCENDING)], name='idx_analysis_tags_en')
    analyses.create_index([('tags_th', ASCENDING)], name='idx_analysis_tags_th')
    analyses.create_index([('tier_key', ASCENDING), ('final_score', DESCENDING)], name='idx_analysis_tier_score')
    analyses.create_index([('final_score', DESCENDING)], name='idx_analysis_final_score_desc')


def close_mongo() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None
