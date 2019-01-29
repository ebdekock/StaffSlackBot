"""
Global settings and constants for the project
"""
import os
import queue
from pathlib import Path

# Third Party
from slackclient import SlackClient

# File locations
LOG_LOCATION = Path.cwd() / "log" / "bot.log"
DATABASE_LOCATION = Path.cwd() / "data" / "bot.sqlite"

# Used to connect to Slack API
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
# Needed for interactive messages
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
# Bot's Slack client, user ID and events queue: assigned after the bot starts up
SLACK_CLIENT = STAFF_BOT_ID = SLACK_EVENTS_Q = None

# Delay in seconds between checking Slack real time session for new events
SLACK_RTM_READ_DELAY = 0.5
# Queue get is blocking, we want a time in seconds out if we need to bail. Useful for
# safe shutdown of bot.
QUEUE_TIMEOUT = 5
# How long in seconds do users have to guess challenge before it times out. Will be
# a range that has additional 10 seconds on top of this time.
CHALLENGE_TIMEOUT = 30

# Filter active users by specific company email address.
# Useful if you have third party consultants that you want
# to exclude. Set to @ for all users in your Slack Channel.
COMPANY_SLACK_EMAIL = "@"

# Command used to start a new guessing game
PLAY_GAME = "play"


def slack_init():
    """
    Initialise Slack connection and configure global vars.
    Should be run once when the bot starts up.
    """
    global SLACK_BOT_TOKEN
    global SLACK_CLIENT
    global SLACK_EVENTS_Q
    global STAFF_BOT_ID

    # Init Queue used for Slack events
    SLACK_EVENTS_Q = queue.Queue()

    # Connect to Slack
    SLACK_CLIENT = SlackClient(SLACK_BOT_TOKEN)
    assert SLACK_CLIENT.rtm_connect(
        with_team_state=False
    ), "Can't start real time Slack session"

    # Read bot's user ID by calling Web API method `auth.test`
    STAFF_BOT_ID = SLACK_CLIENT.api_call("auth.test")["user_id"]
    assert STAFF_BOT_ID, "Can't connect to Slack API"
