"""
Global settings and constants for the project
"""
import os
import queue
from pathlib import Path

# Third Party
from loguru import logger
from slackclient import SlackClient

from typing import Any, Optional

# File locations
LOG_LOCATION: Path = Path.cwd() / "log" / "bot.log"
DATABASE_LOCATION: Path = Path.cwd() / "data" / "bot.sqlite"

# Used to connect to Slack API
SLACK_BOT_TOKEN: Optional[str] = os.getenv("SLACK_BOT_TOKEN")
# Needed for interactive messages
SLACK_SIGNING_SECRET: Optional[str] = os.getenv("SLACK_SIGNING_SECRET")
# Init Slack events queue
SLACK_EVENTS_Q: queue.Queue = queue.Queue()

# Bot's Slack client and user ID: assigned after the bot starts up
SLACK_CLIENT: Any = None
STAFF_BOT_ID: Optional[str] = None

# Delay in seconds between checking Slack real time session for new events
# Use a lower value for larger servers or if you experience delays in responses.
SLACK_RTM_READ_DELAY = 0.05
# Queue get is blocking, we want a time in seconds out if we need to bail. Useful for
# safe shutdown of bot.
QUEUE_TIMEOUT = 5
# How long in seconds do users have to guess challenge before it times out. Will be
# a range that has additional 10 seconds on top of this time.
CHALLENGE_TIMEOUT = 30

# Command used to start a new guessing game
PLAY_GAME = "play"


def slack_init() -> None:
    """
    Initialise Slack connection and configure global vars.
    Should be run once when the bot starts up.
    """
    global SLACK_BOT_TOKEN
    global SLACK_CLIENT
    global STAFF_BOT_ID
    global LOG_LOCATION

    # Configure loguru
    # This allows us to add @logger.catch decorator
    # to any functions to catch unhandled exceptions.
    logger.add(
        LOG_LOCATION,  # Log file
        enqueue=True,  # Enables thread safe logging
        backtrace=True,  # Enables stack trace logging
        rotation="100 MB",  # Rotates when log reaches 100MB
        retention=2,  # Keep two archived logs
        compression="gz",  # Compress rotated logs
    )

    # Connect to Slack
    SLACK_CLIENT = SlackClient(SLACK_BOT_TOKEN)
    assert SLACK_CLIENT.rtm_connect(
        with_team_state=False
    ), "Can't start real time Slack session"

    # Read bot's user ID by calling Web API method `auth.test`
    STAFF_BOT_ID = SLACK_CLIENT.api_call("auth.test")["user_id"]
    assert STAFF_BOT_ID, "Can't connect to Slack API"
