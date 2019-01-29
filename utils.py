import logging

# Third party
from slackclient import SlackClient

# Local
import settings
from models import User
from sql import create_users_table


def enable_logging():
    """
    Enable info level logging in this format:
    DATE       TIME           LEVEL  MESSAGE
    2018-11-13 21:04:43,881 - INFO - Bot connected and running!

    :returns: a python logger object
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(settings.LOG_LOCATION)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def get_users_from_slack():
    """
    Syncs our database with Slack. Create any active
    users and delete any disabled users from the database.
    """

    # Create users table if it doesnt exist
    create_users_table()

    # Get all users IM channels with bot
    channels = get_slack_users_channels()

    # Get 100 users from Slack at a time (Slacks recommendation), its
    # paginated, so we loop until we get all users
    users = []
    slack_users = settings.SLACK_CLIENT.api_call("users.list", limit=100)
    has_more = True
    while has_more:
        if slack_users["ok"]:
            if slack_users["members"]:
                users.extend(slack_users["members"])
            # If this is null, we've looped through all pages
            has_more = bool(slack_users["response_metadata"]["next_cursor"])
            if has_more:
                # Get next page
                cursor = slack_users["response_metadata"]["next_cursor"]
                slack_users = settings.SLACK_CLIENT.api_call(
                    "users.list", cursor=cursor, limit=100
                )
        else:
            # Something went wrong
            has_more = False
    # Update DB
    for user in users:
        current_user = User.parse_slack_data(user)
        if is_active_slack_user(user):
            current_user.slack_channel = channels.get(current_user.slack_id)
            current_user.save()
        else:
            current_user.delete()


def get_slack_users_channels():
    """
    Get all direct channels for users on Slack to be stored in DB,
    this will allow us to immediately message users without needing
    to get their channel from Slack.
    """
    # Get 100 channels from Slack at a time (Slacks recommendation), its
    # paginated, so we loop until we get all channels
    channels = {}
    slack_channels = settings.SLACK_CLIENT.api_call(
        "conversations.list", types="im", limit=100
    )
    has_more = True
    while has_more:
        if slack_channels["ok"]:
            for channel in slack_channels["channels"]:
                channels[channel["user"]] = channel["id"]
            # If this is null, we've looped through all pages
            has_more = bool(slack_channels["response_metadata"]["next_cursor"])
            if has_more:
                # Get next page
                cursor = slack_channels["response_metadata"]["next_cursor"]
                slack_channels = settings.SLACK_CLIENT.api_call(
                    "conversations.list", types="im", cursor=cursor, limit=100
                )
        else:
            # Something went wrong
            has_more = False
    return channels


def is_active_slack_user(user):
    """
    Returns true for non-bot and active users.
    Also ensures the user is using company email
    if filtering enabled.

    See https://api.slack.com/types/user
    :param data: a dictionary from slack api with fields as per above
    :returns: True or False
    """
    if not user.get("deleted") and not user.get("is_bot"):
        email = user.get("profile").get("email")
        if email and settings.COMPANY_SLACK_EMAIL in email:
            return True
    return False
