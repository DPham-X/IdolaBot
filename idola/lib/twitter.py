import datetime
import logging
import pickle

import pytz
import twitter
from google_trans_new import google_translator

logger = logging.getLogger(f"idola.{__name__}")


class TwitterAPI:
    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        access_token_key: str,
        access_token_secret: str,
    ):
        self.api = None
        self.existing_tweets = set()
        self.bot_start_ts = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        self.db_location = "tweet_ids.p"
        self.screen_name = "sega_idola"
        self.access_token_key = access_token_key
        self.access_token_secret = access_token_secret
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret

        self.load_existing_tweets()
        self.start()

    def load_existing_tweets(self) -> bool:
        if not self.db_location:
            return

        try:
            logger.info(f"Loading existing tweets from {self.db_location}")
            with open(self.db_location, "rb") as f:
                self.existing_tweets = pickle.load(f)
        except FileNotFoundError as e:
            logger.error(f"Error: Could not load existing tweets: {e}")
            return False
        except EOFError as e:
            logger.error(f"Error: Could not unpickle file: {e}")
            self.existing_tweets = set()
        return True

    def save_existing_tweets(self) -> None:
        with open(self.db_location, "wb") as f:
            pickle.dump(self.existing_tweets, f)

    def start(self) -> None:
        self.api = twitter.Api(
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            access_token_key=self.access_token_key,
            access_token_secret=self.access_token_secret,
            sleep_on_rate_limit=True,
            tweet_mode="extended",
        )

    def get_tweets(self):
        logger.info(f"Fetching tweets for @{self.screen_name}")
        unseen_tweets = []
        tweets = self.api.GetUserTimeline(
            screen_name=self.screen_name,
            exclude_replies=True,
            include_rts=True,
            count=5,
        )
        for tweet in tweets:
            if tweet.id in self.existing_tweets:
                continue
            unseen_tweets.insert(0, tweet)
            self.existing_tweets.add(tweet.id)
        if unseen_tweets:
            self.save_existing_tweets()
        return unseen_tweets

    def get_test_tweet(self):
        logger.info(f"Fetching tweets for @{self.screen_name}")
        tweets = self.api.GetUserTimeline(
            screen_name=self.screen_name,
            exclude_replies=True,
            include_rts=True,
            count=1,
        )
        return tweets[0] if len(tweets) != 1 else None

    def translate(self, message):
        try:
            translator = google_translator()
            message = message.replace("イドラ", "IDOLA")
            translated_text = translator.translate(message, lang_src="ja", lang_tgt="en")
            return translated_text
        except Exception as e:
            logger.exception(e)
        return message
