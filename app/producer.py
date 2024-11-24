from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
from kafka import KafkaProducer
import tweepy
import json
import os
import redis
from datetime import datetime
from dotenv import load_dotenv
from logger import log_info, log_error
import threading
import asyncio
from typing import Optional, Dict, List
import time

wait_on_rate_limit = False

# Load environment variables
load_dotenv()

# Configuration
BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN_PRODUCER')
USERNAME = os.getenv('TWITTER_USERNAME')
KAFKA_SERVERS = os.getenv('KAFKA_SERVERS', 'localhost:9092')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
KAFKA_TOPIC = 'twitter.mentions'

# Initialize FastAPI
app = FastAPI(title="Twitter Mentions Producer Service")

def append_to_json(filename: str, new_item: dict):
    """
    Append a new item to a JSON file. If the file doesn't exist,
    it will be created with the item in a list.
    
    Args:
        filename (str): Path to the JSON file
        new_item (dict): New item to append to the JSON file
    """
    # Create empty list if file doesn't exist
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            json.dump([], f)
    
    # Read existing data
    with open(filename, 'r') as f:
        data = json.load(f)
    
    # Append new item
    data.append(new_item)
    
    # Write back to file
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

# Global variables for producer management
is_running = threading.Event()
fetch_interval = 60  # 1 minutes
processed_count = 0
error_count = 0
last_fetch_time = None
background_task: Optional[asyncio.Task] = None

class TwitterClient:
    def __init__(self):
        self.client = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            wait_on_rate_limit=wait_on_rate_limit    # Enable/Disable rate limit
        )
        self.user_id = None
        self.redis_client = redis.from_url(REDIS_URL)
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    @property
    def user_id(self):
        if not self._user_id:
            cached_id = self.redis_client.get(f"twitter:user_id:{USERNAME}")
            if cached_id:
                self._user_id = cached_id.decode('utf-8')
            else:
                user = self.client.get_user(username=USERNAME)
                print(str(user.data.id))
                self._user_id = str(user.data.id)
                self.redis_client.set(f"twitter:user_id:{USERNAME}", self._user_id)
        return self._user_id

    async def get_mentions(self) -> List[Dict]:
        """Fetch mentions from Twitter"""
        try:
            last_mention_id = self.redis_client.get(f"twitter:last_mention:{USERNAME}")
            last_mention_id = last_mention_id.decode('utf-8') if last_mention_id else None

            mentions = self.client.get_users_mentions(
                id=self.user_id,
                since_id=last_mention_id,
                tweet_fields=['created_at', 'author_id', 'conversation_id'],
                max_results=5,
                expansions=['referenced_tweets.id']
            )
            # Print rate limit information
            if hasattr(mentions, '_headers'):
                rate_limit = {
                    'limit': mentions._headers.get('x-rate-limit-limit'),
                    'remaining': mentions._headers.get('x-rate-limit-remaining'),
                    'reset': mentions._headers.get('x-rate-limit-reset')
                }
                print(f"Rate Limit Info: {rate_limit}")
                log_info(f"Rate Limits - Remaining: {rate_limit['remaining']}/{rate_limit['limit']}, " 
                        f"Reset at: {rate_limit['reset']}")
                print(mentions)

            if not mentions.data:
                return []

            mentions_data = []
            newest_id = last_mention_id

            print(mentions.data)

            for mention in mentions.data:
                mention_data = {
                    'id': str(mention.id),
                    'text': mention.text,
                    'author_id': str(mention.author_id),
                    'conversation_id': str(mention.conversation_id),
                    'created_at': mention.created_at.isoformat() if mention.created_at else None,
                    'processed_at': datetime.now().isoformat()
                }

                if not newest_id or int(mention.id) > int(newest_id):
                    newest_id = str(mention.id)

                mentions_data.append(mention_data)

            if newest_id:
                self.redis_client.set(f"twitter:last_mention:{USERNAME}", newest_id)

            append_to_json('mentions.json', mentions_data)
            return mentions_data

        except Exception as e:
            log_error(f"Error fetching mentions: {str(e)}")
            raise

    async def process_mentions(self, mentions: List[Dict]):
        """Send mentions to Kafka"""
        global processed_count, error_count
        
        try:
            for mention in mentions:
                # Log mentions in a json file
                append_to_json('mentions.json', mention)
                self.producer.send(
                    KAFKA_TOPIC,
                    value=mention,
                    key=str(mention['author_id']).encode('utf-8')
                )
            self.producer.flush()
            processed_count += len(mentions)
            log_info(f"Sent {len(mentions)} mentions to Kafka")
            return True
        except Exception as e:
            error_count += 1
            log_error(f"Error sending to Kafka: {str(e)}")
            raise

async def continuous_mention_fetch():
    """Background task for continuously fetching mentions"""
    global last_fetch_time
    
    twitter_client = TwitterClient()
    
    while is_running.is_set():
        try:
            mentions = await twitter_client.get_mentions()
            if mentions:
                await twitter_client.process_mentions(mentions)
            
            last_fetch_time = datetime.now().isoformat()
            await asyncio.sleep(fetch_interval)
            
        except Exception as e:
            log_error(f"Error in continuous mention fetch: {str(e)}")
            await asyncio.sleep(60)  # Wait a minute before retrying on error

@app.on_event("startup")
async def startup_event():
    """Start the continuous mention fetch when the FastAPI app starts"""
    await start_producer()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the continuous mention fetch when the FastAPI app shuts down"""
    await stop_producer()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to the Twitter Mentions Producer Service!",
        "status": "running" if is_running.is_set() else "stopped"
    }

@app.get("/status")
async def get_status():
    """Get the current status of the producer"""
    return {
        "is_running": is_running.is_set(),
        "last_fetch_time": last_fetch_time,
        "fetch_interval": fetch_interval,
        "processed_count": processed_count,
        "error_count": error_count
    }

@app.post("/start")
async def start_producer():
    """Start the continuous mention fetch"""
    global background_task
    
    if is_running.is_set():
        return {"message": "Producer is already running"}
    
    is_running.set()
    background_task = asyncio.create_task(continuous_mention_fetch())
    
    return {"message": "Producer started successfully"}

@app.post("/stop")
async def stop_producer():
    """Stop the continuous mention fetch"""
    global background_task
    
    if not is_running.is_set():
        return {"message": "Producer is not running"}
    
    is_running.clear()
    
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
        background_task = None
    
    return {"message": "Producer stopped successfully"}

@app.post("/fetch")
async def manual_fetch(background_tasks: BackgroundTasks):
    """Manually trigger a mention fetch"""
    try:
        # Check rate limit
        twitter_client = TwitterClient()
        rate_key = f"twitter:rate_limit:{USERNAME}"
        
        if twitter_client.redis_client.get(rate_key):
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit reached. Please try again later."}
            )

        # Set rate limit (1 minutes)
        twitter_client.redis_client.setex(rate_key, 60, "1")

        mentions = await twitter_client.get_mentions()

        if mentions:
            background_tasks.add_task(twitter_client.process_mentions, mentions)
            return {"message": f"Found and processing {len(mentions)} mentions"}
        
        return {"message": "No new mentions found"}

    except Exception as e:
        log_error(f"Error in manual fetch: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/metrics")
async def get_metrics():
    """Get producer metrics"""
    return {
        "processed_mentions": processed_count,
        "errors": error_count,
        "uptime": "Running" if is_running.is_set() else "Stopped",
        "last_fetch": last_fetch_time,
        "fetch_interval_seconds": fetch_interval,
        "kafka_topic": KAFKA_TOPIC,
        "twitter_username": USERNAME
    }

@app.put("/config")
async def update_config(new_interval: int):
    """Update the fetch interval"""
    global fetch_interval
    
    if new_interval < 60:  # Don't allow intervals less than 1 minute
        return JSONResponse(
            status_code=400,
            content={"error": "Interval must be at least 60 seconds"}
        )
    
    fetch_interval = new_interval
    return {"message": f"Fetch interval updated to {new_interval} seconds"}