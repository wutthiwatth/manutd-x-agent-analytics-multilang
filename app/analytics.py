from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import requests
from pymongo import UpdateOne

from .config import config
from .mongo import get_tweet_analyses_collection, get_tweets_collection

ANALYSIS_VERSION = 1
CATEGORIES = [
    'transfer',
    'injury',
    'match',
    'lineup',
    'contract',
    'club_news',
    'academy',
    'finance',
    'rumour',
    'quote',
    'other',
]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def safe_number(value: Any, fallback: float) -> float:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else fallback


def safe_string(value: Any, fallback: str = '') -> str:
    return value if isinstance(value, str) else fallback


def safe_string_array(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def output_text_from_response(response: dict[str, Any]) -> str:
    if isinstance(response.get('output_text'), str):
        return response['output_text']

    chunks: list[str] = []
    for item in response.get('output', []) or []:
        for content in item.get('content', []) or []:
            if content.get('type') == 'output_text' and isinstance(content.get('text'), str):
                chunks.append(content['text'])
    return '\n'.join(chunks).strip()


def response_schema() -> dict[str, Any]:
    return {
        'type': 'object',
        'additionalProperties': False,
        'required': ['items'],
        'properties': {
            'items': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'required': [
                        'tweet_id',
                        'summary_th',
                        'summary_en',
                        'category',
                        'tags',
                        'tags_en',
                        'tags_th',
                        'entities',
                        'sentiment',
                        'confidence',
                        'importance_score',
                        'is_rumour',
                    ],
                    'properties': {
                        'tweet_id': {'type': 'string'},
                        'summary_th': {'type': 'string'},
                        'summary_en': {'type': 'string'},
                        'category': {'type': 'string', 'enum': CATEGORIES},
                        'tags': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'Backward-compatible English tags; same as tags_en.',
                        },
                        'tags_en': {'type': 'array', 'items': {'type': 'string'}},
                        'tags_th': {'type': 'array', 'items': {'type': 'string'}},
                        'entities': {
                            'type': 'object',
                            'additionalProperties': False,
                            'required': ['players', 'clubs', 'competitions', 'people'],
                            'properties': {
                                'players': {'type': 'array', 'items': {'type': 'string'}},
                                'clubs': {'type': 'array', 'items': {'type': 'string'}},
                                'competitions': {'type': 'array', 'items': {'type': 'string'}},
                                'people': {'type': 'array', 'items': {'type': 'string'}},
                            },
                        },
                        'sentiment': {'type': 'string', 'enum': ['positive', 'neutral', 'negative']},
                        'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
                        'importance_score': {'type': 'number', 'minimum': 0, 'maximum': 100},
                        'is_rumour': {'type': 'boolean'},
                    },
                },
            }
        },
    }


def build_input_tweets(tweets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    input_tweets: list[dict[str, Any]] = []
    for tweet in tweets:
        ingest = tweet.get('_ingest') or {}
        input_tweets.append(
            {
                'tweet_id': tweet.get('id'),
                'text': tweet.get('text'),
                'url': tweet.get('url'),
                'created_at': tweet.get('created_at'),
                'author': ingest.get('author_x_username'),
                'source_type': ingest.get('source_type'),
                'tier_key': ingest.get('tier_key'),
                'tier_name': ingest.get('tier_name'),
                'reliability_score': ingest.get('reliability_score'),
                'public_metrics': tweet.get('public_metrics'),
            }
        )
    return input_tweets


def call_openai(tweets: list[dict[str, Any]]) -> dict[str, Any]:
    body = {
        'model': config.openai_model,
        'input': [
            {
                'role': 'system',
                'content': (
                    'You analyze Manchester United related X posts. Return concise Thai and English summaries, '
                    'useful bilingual tags, category, entities, and scores. Do not invent facts beyond the tweet text. '
                    'Keep tags_en in lower_snake_case English. Keep tags_th as short Thai labels.'
                ),
            },
            {
                'role': 'user',
                'content': json.dumps({'tweets': build_input_tweets(tweets)}, ensure_ascii=False, indent=2),
            },
        ],
        'text': {
            'format': {
                'type': 'json_schema',
                'name': 'tweet_analysis_batch',
                'strict': True,
                'schema': response_schema(),
            }
        },
        'temperature': 0.2,
        'max_output_tokens': config.openai_max_output_tokens,
        'store': False,
    }

    response = requests.post(
        'https://api.openai.com/v1/responses',
        headers={
            'Authorization': f'Bearer {config.openai_api_key}',
            'Content-Type': 'application/json',
        },
        json=body,
        timeout=120,
    )

    if not response.ok:
        raise RuntimeError(f'OpenAI API error {response.status_code}: {response.text}')

    response_json = response.json()
    output_text = output_text_from_response(response_json)
    if not output_text:
        raise RuntimeError(f'OpenAI response did not include output text: {response.text}')

    return json.loads(output_text)


def load_tweets_for_analysis(limit: int) -> list[dict[str, Any]]:
    tweets = get_tweets_collection()
    if config.retry_failed:
        analytics_filter: dict[str, Any] = {'$nin': ['done', 'pending']}
    else:
        analytics_filter = {'$exists': False}

    query = {
        'text': {'$exists': True, '$type': 'string', '$ne': ''},
        '$or': [
            {'_analytics.status': {'$exists': False}},
            {'_analytics.status': analytics_filter},
        ],
    }
    return list(tweets.find(query).sort('created_at', -1).limit(limit))


def build_analysis_doc(tweet: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    ingest = tweet.get('_ingest') or {}
    reliability_score = safe_number(ingest.get('reliability_score'), 50)
    importance_score = safe_number(item.get('importance_score'), 50)
    final_score = round(importance_score * 0.7 + reliability_score * 0.3)
    tags = safe_string_array(item.get('tags'))
    tags_en = safe_string_array(item.get('tags_en')) or tags

    entities = item.get('entities') or {}
    if not isinstance(entities, dict):
        entities = {}

    return {
        '_id': tweet.get('id'),
        'tweet_id': tweet.get('id'),
        'tweet_url': tweet.get('url'),
        'author_x_username': ingest.get('author_x_username'),
        'source_id': ingest.get('source_id'),
        'source_type': ingest.get('source_type'),
        'tier_key': ingest.get('tier_key'),
        'tier_name': ingest.get('tier_name'),
        'reliability_score': ingest.get('reliability_score'),
        'summary_th': safe_string(item.get('summary_th')),
        'summary_en': safe_string(item.get('summary_en')),
        'category': item.get('category') if item.get('category') in CATEGORIES else 'other',
        'tags': tags_en,
        'tags_en': tags_en,
        'tags_th': safe_string_array(item.get('tags_th')),
        'entities': {
            'players': safe_string_array(entities.get('players')),
            'clubs': safe_string_array(entities.get('clubs')),
            'competitions': safe_string_array(entities.get('competitions')),
            'people': safe_string_array(entities.get('people')),
        },
        'sentiment': item.get('sentiment') if item.get('sentiment') in {'positive', 'neutral', 'negative'} else 'neutral',
        'confidence': safe_number(item.get('confidence'), 0.5),
        'importance_score': importance_score,
        'final_score': final_score,
        'is_rumour': bool(item.get('is_rumour')),
        'openai_model': config.openai_model,
        'analysis_version': ANALYSIS_VERSION,
        'analyzed_at': now_utc(),
    }


def run_analytics_once() -> int:
    tweets_collection = get_tweets_collection()
    analyses_collection = get_tweet_analyses_collection()
    tweets = load_tweets_for_analysis(config.analytics_batch_size)

    if not tweets:
        print('[analytics] No tweets pending analysis.', flush=True)
        return 0

    tweet_ids = [tweet.get('id') for tweet in tweets if tweet.get('id')]
    print(f'[analytics] Analyzing {len(tweets)} tweet(s)...', flush=True)

    tweets_collection.update_many(
        {'id': {'$in': tweet_ids}},
        {'$set': {'_analytics.status': 'pending'}},
    )

    try:
        model_response = call_openai(tweets)
        items = model_response.get('items') if isinstance(model_response, dict) else []
        if not isinstance(items, list):
            items = []

        item_by_id = {str(item.get('tweet_id')): item for item in items if isinstance(item, dict) and item.get('tweet_id')}
        docs = []
        for tweet in tweets:
            tweet_id = tweet.get('id')
            item = item_by_id.get(str(tweet_id))
            if item:
                docs.append(build_analysis_doc(tweet, item))

        if not docs:
            raise RuntimeError('Model returned no matching tweet analyses.')

        operations = [
            UpdateOne({'tweet_id': doc['tweet_id']}, {'$set': doc}, upsert=True)
            for doc in docs
        ]
        analyses_collection.bulk_write(operations, ordered=False)

        analyzed_ids = [doc['tweet_id'] for doc in docs]
        tweets_collection.update_many(
            {'id': {'$in': analyzed_ids}},
            {'$set': {'_analytics.status': 'done', '_analytics.analyzed_at': now_utc()}},
        )

        print(f'[analytics] Done. analyzed={len(docs)}', flush=True)
        return len(docs)
    except Exception as exc:
        message = str(exc)
        tweets_collection.update_many(
            {'id': {'$in': tweet_ids}},
            {'$set': {'_analytics.status': 'failed', '_analytics.error': message}},
        )
        raise
