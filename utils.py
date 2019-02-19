from typing import Dict, List

# Third party
from loguru import logger

# Local
import settings as s
from models import User
from sql import create_users_table


@logger.catch
def get_users_from_slack() -> None:
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
    users: List = []
    slack_users = s.SLACK_CLIENT.api_call("users.list", limit=100)
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
                slack_users = s.SLACK_CLIENT.api_call(
                    "users.list", cursor=cursor, limit=100
                )
        else:
            # Something went wrong
            has_more = False
    # Update DB
    for user in users:
        current_user = User.parse_slack_data(user)
        if current_user and is_active_slack_user(user):
            current_user.slack_channel = channels.get(current_user.slack_id)
            current_user.save()
        elif current_user:
            current_user.delete()

    logger.info(f"Successfully updated users from Slack.")


@logger.catch
def get_slack_users_channels() -> Dict[str, str]:
    """
    Get all direct channels for users on Slack to be stored in DB,
    this will allow us to immediately message users without needing
    to get their channel from Slack.
    """
    # Get 100 channels from Slack at a time (Slacks recommendation), its
    # paginated, so we loop until we get all channels
    channels = {}
    slack_channels = s.SLACK_CLIENT.api_call(
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
                slack_channels = s.SLACK_CLIENT.api_call(
                    "conversations.list", types="im", cursor=cursor, limit=100
                )
        else:
            # Something went wrong
            has_more = False
    return channels


def is_active_slack_user(user: Dict) -> bool:
    """
    Returns true for non-bot and active users.
    Only returns true for users with email
    addresses, if you dont have an email
    its assumed you are bot.

    See https://api.slack.com/types/user
    """
    if not user.get("deleted") and not user.get("is_bot"):
        profile = user.get("profile")
        if profile:
            if profile.get("email"):
                return True
    return False
