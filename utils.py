from typing import Dict, List

# Third party
import cv2
import requests
from loguru import logger
import numpy as np

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
            # Get their Slack channel
            current_user.slack_channel = channels.get(current_user.slack_id)
            current_user.save()
        elif current_user:
            # Remove user from DB if they aren't active
            current_user.delete()

    # Update all users profiles if they have a face in their avatar
    if s.ENABLE_FACE_DETECTION:
        detect_face(User.get_all_users())

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


@logger.catch
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


@logger.catch
def detect_face(users: List) -> None:
    """
    Uses two Haar Classifiers to try and determine if there is a face
    present in the users Slack avatar - if face detection is enabled. Its
    not super accurate and its mostly to get rid of the stock image from
    Slack and super obvious pictures that won't be able to help users determine
    who it is.
    """
    # We use two classifiers to try and determine if there is a face present
    cascades = [
        cv2.CascadeClassifier(
            f"{cv2.data.haarcascades}haarcascade_frontalface_default.xml"
        ),
        cv2.CascadeClassifier(f"{cv2.data.haarcascades}haarcascade_profileface.xml"),
    ]
    # Go through all users and ensure they are valid for the guessing game
    for user in users:
        can_play_game = False
        for cascade in cascades:
            if can_play_game:
                # Don't need to look further
                break
            # Retrieve image
            r = requests.get(user.photo_url)
            r.raise_for_status()
            # Convert to numpy array so that we can decode it
            image = np.asarray(bytearray(r.content), dtype="uint8")
            image = cv2.imdecode(image, cv2.IMREAD_COLOR)
            # Convert to grey scale for cv2 recognition
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # Detect faces in the image
            faces_found = cascade.detectMultiScale(
                gray, scaleFactor=1.05, minNeighbors=5, minSize=(30, 30)
            )
            if len(faces_found) > 0:
                can_play_game = True
        # Save to DB
        user.can_play_game = can_play_game
        user.save()
