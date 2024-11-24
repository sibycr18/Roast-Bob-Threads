**Twitter Roasting Bot**
=========================

**Table of Contents**
-----------------

1. [Project Overview](#project-overview)
2. [How it Works](#how-it-works)
3. [Prerequisites](#prerequisites)
4. [Setup](#setup)
5. [Environment Variables](#environment-variables)
6. [Running the Bot](#running-the-bot)
7. [Project Structure](#project-structure)
8. [Troubleshooting](#troubleshooting)

**Project Overview**
-------------------

The Twitter Roasting Bot is a Python-based project that uses natural language processing (NLP) and machine learning (ML) to generate humorous roasts in response to tweets that mention the bot. The bot is designed to engage with users on Twitter and provide a fun and entertaining experience.

**How it Works**
----------------

Here's a high-level overview of how the bot works:

1. **Tweet Collection**: The bot uses the Twitter API to collect tweets that mention the bot's handle.
2. **Text Analysis**: The bot uses NLP techniques to analyze the text of the collected tweets and identify the user's intent and sentiment.
3. **Roast Generation**: Based on the analysis, the bot generates a humorous roast using a combination of machine learning algorithms and pre-defined templates.
4. **Response**: The bot responds to the original tweet with the generated roast.

**Prerequisites**
---------------

* Python 3.x
* pip
* Twitter API keys (consumer key, consumer secret, access token, access token secret)
* Together AI credentials (API key, API secret)

**Setup**
--------

1. Clone the repository: `git clone https://github.com/your-username/twitter-roasting-bot.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Create a new file named `.env` in the root directory of the project
4. Add your Twitter API keys and Together AI credentials to the `.env` file.

**Environment Variables**
-------------------------

```makefile
TWITTER_CONSUMER_KEY=your-consumer-key
TWITTER_CONSUMER_SECRET=your-consumer-secret
TWITTER_ACCESS_TOKEN=your-access-token
TWITTER_ACCESS_TOKEN_SECRET=your-access-token-secret
TOGETHER_AI_API_KEY=your-together-ai-api-key
```

The project uses environment variables to store sensitive information such as Twitter API keys and Together AI credentials. You can set these variables in the `.env` file or as system environment variables.

**Running the Bot**
------------------

1. Run the bot: `uvicorn main:app --reload`
2. The bot will start listening for mentions on Twitter and respond with roasts

**Project Structure**
---------------------

* `main.py`: The main application file that runs the bot
* `twitter.py`: A module that handles Twitter API interactions
* `together_ai.py`: A module that handles Together AI API interactions
* `roast.py`: A module that generates roasts
* `requirements.txt`: A file that lists the project dependencies

**Troubleshooting**
------------------

* If you encounter issues with the bot, check the logs for errors
* Make sure your Twitter API keys and Together AI credentials are correct
* If you're still having issues, feel free to open an issue on the GitHub repository
