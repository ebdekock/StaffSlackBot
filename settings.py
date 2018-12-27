""" 
Global settings and constants for the project
"""

import logging
import os

from pathlib import Path

### File locations ###
LOG_LOCATION = Path.cwd() / "log" / "bot.log"
DATABASE_LOCATION = Path.cwd() / "data" / "bot.sqlite"

### Constants ###
# Used to connect to Slack API
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
# Needed for interactive messages
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

# Filter active users by specific company email address.
# Set to @ for all users in your Slack Channel.
COMPANY_SLACK_EMAIL = "@"


def enable_logging():
    """
    Enable info level logging in this format:
    DATE       TIME           LEVEL  MESSAGE
    2018-11-13 21:04:43,881 - INFO - Bot connected and running!

    :returns: a python logger object
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(LOG_LOCATION)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
