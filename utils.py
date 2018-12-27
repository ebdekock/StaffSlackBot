from slackclient import SlackClient

import settings

from models import User
from sql import create_users_table


def get_users_from_slack():
    """ 
    Syncs our database with Slack. Create any active
    users and delete any disabled users from the database. 
    """

    # Create users table if it doesnt exist
    create_users_table()

    # Connect to Slack
    slack_client = SlackClient(settings.SLACK_BOT_TOKEN)
    assert slack_client.rtm_connect(with_team_state=False), "Cant connect to slack"

    # Get all users
    all_slack_users = slack_client.api_call("users.list")
    if all_slack_users["ok"] and all_slack_users["members"]:
        for user in all_slack_users["members"]:
            current_user = User.parse_slack_data(user)
            if is_active_slack_user(user):
                current_user.save()
            else:
                current_user.delete()


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
