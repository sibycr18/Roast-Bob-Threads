from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
from kafka import KafkaConsumer
import json
import os
import tweepy
from roaster import generate_roast
from logger import log_info, log_error
from dotenv import load_dotenv
import time
from typing import Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

wait_on_rate_limit = True

# Load environment variables
load_dotenv()

# Configuration
KAFKA_SERVERS = os.getenv('KAFKA_SERVERS', 'localhost:9092')
KAFKA_TOPIC = 'twitter.mentions'
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
ROAST_STYLE = os.getenv('ROAST_STYLE', 'savage')

# Initialize FastAPI
app = FastAPI(title="Twitter Roaster Consumer Service")

# Global variables for consumer management
consumer_thread: Optional[threading.Thread] = None
should_consume = threading.Event()
is_consuming = threading.Event()
processed_count = 0
error_count = 0

class TwitterReplier:
    def __init__(self):
        self.client = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True
        )

    def reply_to_tweet(self, tweet_id: str, reply_text: str):
        try:
            self.client.create_tweet(
                text=reply_text,
                in_reply_to_tweet_id=tweet_id
            )
            log_info(f"Successfully replied to tweet {tweet_id}")
            return True
        except Exception as e:
            log_error(f"Error replying to tweet {tweet_id}: {str(e)}")
            return False

def process_mention(mention: dict, twitter_client: TwitterReplier):
    global processed_count, error_count
    try:
        tweet_id = mention['id']
        tweet_text = mention['text']
        
        roast = generate_roast(ROAST_STYLE, tweet_text)
        success = twitter_client.reply_to_tweet(tweet_id, roast)
        
        if success:
            processed_count += 1
            log_info(f"Successfully processed mention {tweet_id}")
        else:
            error_count += 1
            log_error(f"Failed to process mention {tweet_id}")
            
    except Exception as e:
        error_count += 1
        log_error(f"Error processing mention: {str(e)}")

def kafka_consumer_loop():
    """Background task for consuming Kafka messages"""
    global is_consuming
    
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='twitter_roaster_group',
            auto_offset_reset='latest'
        )
        
        twitter_client = TwitterReplier()
        log_info("Starting Twitter mentions consumer...")
        
        is_consuming.set()
        
        while should_consume.is_set():
            try:
                # Use poll() instead of iteration to allow for clean shutdown
                messages = consumer.poll(timeout_ms=1000)
                
                for topic_partition, partition_messages in messages.items():
                    for message in partition_messages:
                        mention = message.value
                        log_info(f"Received mention: {mention['id']}")
                        process_mention(mention, twitter_client)
                        time.sleep(2)  # Rate limiting
                        
            except Exception as e:
                log_error(f"Error processing message batch: {str(e)}")
                error_count += 1
                continue
                
    except Exception as e:
        log_error(f"Fatal error in consumer: {str(e)}")
    finally:
        is_consuming.clear()
        if 'consumer' in locals():
            consumer.close()

@app.on_event("startup")
async def startup_event():
    """Start the Kafka consumer when the FastAPI app starts"""
    await start_consumer()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the Kafka consumer when the FastAPI app shuts down"""
    await stop_consumer()

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Twitter Roaster Consumer Service"}

@app.get("/status")
async def get_status():
    """Get the current status of the consumer"""
    return {
        "is_running": is_consuming.is_set(),
        "processed_count": processed_count,
        "error_count": error_count
    }

@app.post("/start")
async def start_consumer():
    """Start the Kafka consumer"""
    global consumer_thread
    
    if is_consuming.is_set():
        return {"message": "Consumer is already running"}
    
    should_consume.set()
    consumer_thread = threading.Thread(target=kafka_consumer_loop)
    consumer_thread.start()
    
    # Wait for consumer to start
    start_time = time.time()
    while not is_consuming.is_set() and time.time() - start_time < 10:
        await asyncio.sleep(0.1)
    
    if is_consuming.is_set():
        return {"message": "Consumer started successfully"}
    else:
        should_consume.clear()
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to start consumer"}
        )

@app.post("/stop")
async def stop_consumer():
    """Stop the Kafka consumer"""
    global consumer_thread
    
    if not is_consuming.is_set():
        return {"message": "Consumer is not running"}
    
    should_consume.clear()
    
    if consumer_thread:
        consumer_thread.join(timeout=10)
        consumer_thread = None
    
    return {"message": "Consumer stopped successfully"}

@app.get("/metrics")
async def get_metrics():
    """Get consumer metrics"""
    return {
        "processed_mentions": processed_count,
        "errors": error_count,
        "uptime": "Running" if is_consuming.is_set() else "Stopped",
        "kafka_topic": KAFKA_TOPIC,
        "roast_style": ROAST_STYLE
    }

if __name__ == "__main__":
    process_mention(
        {
            "id": "1860331398818840725",
            "text": "@Roast_Bob_AI roast this in samay raina style",
            "created_at": "2024-11-23T14:35:43+00:00",
            "author_id": "966993210412212224",
            "saved_at": "2024-11-23T22:15:07.988114"
        }
        , twitter_client=TwitterReplier())