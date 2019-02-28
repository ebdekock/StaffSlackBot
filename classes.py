import queue
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Tuple, Union

# Third party
import schedule
from loguru import logger

# Local
import settings as s
from fields import StringField
from models import User
from sql import fetch_all_rows_sql, fetch_one_row_sql
from utils import get_users_from_slack


class SlackEvent:
    """
    A SlackEvent is just a message within Slack. Currently
    we only care about the message user and their message.
    """

    # Strict type enforcing on fields
    user = StringField(upper_case=True)
    message = StringField()

    def __init__(self, user: str, message: str) -> None:
        self.user = user
        self.message = message

    @staticmethod
    def parse_direct_mention(
        message_text: str
    ) -> Union[Tuple[str, str], Tuple[None, None]]:
        """
        Finds a direct mention (@botname that is at the
        beginning) in message text.
        """
        # From https://www.fullstackpython.com/blog/build-first-slack-bot-python.html
        MENTION_REGEX = "^<@(|[WU].+?)>(.*)"
        matches = re.search(MENTION_REGEX, message_text, re.IGNORECASE)
        return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

    @staticmethod
    def is_direct_message(channel: str) -> bool:
        """
        See if a message was a direct message (IM/whisper) to our bot.
        """
        # Create query
        sql = "SELECT * FROM users WHERE slack_channel = ?"
        user = fetch_one_row_sql(sql, (channel,))
        return bool(user)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.user!r}, {self.message!r})"


class MonitorSlack(threading.Thread):
    """
    Checks Slack API regularly for new events
    (messages from users) and adds it to the Queue.
    """

    def __init__(self) -> None:
        super(MonitorSlack, self).__init__()
        self._stop_event = threading.Event()

    def queue_slack_events(self) -> None:
        """
        Parses a list of events coming from the Slack RTM API to find
        bot mentions or whispers.

        Add SlackEvent to Events Queue
        If its not a direct mention or whisper to our bot, ignore event
        """
        slack_events = s.SLACK_CLIENT.rtm_read()
        for event in slack_events:
            if event.get("type") == "message" and "subtype" not in event:
                # Queue event if its a direct mention or direct message
                user_id, message = SlackEvent.parse_direct_mention(event["text"])
                if user_id == s.STAFF_BOT_ID and message:
                    direct_mention = SlackEvent(event["user"], message)
                    s.SLACK_EVENTS_Q.put(direct_mention)
                elif SlackEvent.is_direct_message(event["channel"]):
                    direct_message = SlackEvent(event["user"], event["text"])
                    s.SLACK_EVENTS_Q.put(direct_message)

    @logger.catch
    def run(self) -> None:
        while True:
            self.queue_slack_events()
            time.sleep(s.SLACK_RTM_READ_DELAY)
            # Check if we need to quit
            if self.stopped():
                break

    def stop(self) -> None:
        self._stop_event.set()

    def stopped(self) -> bool:
        return self._stop_event.is_set()


class ProcessQueue(threading.Thread):
    """
    Checks our Slack Queue regularly for new events.
    It will wait until new events are added and
    then process them appropriately.
    """

    def __init__(self) -> None:
        super(ProcessQueue, self).__init__()
        self._stop_event = threading.Event()

    def resolve_challenge(self, event: SlackEvent, user: User) -> None:
        """
        If the user currently has a challenge, we resolve it,
        see if they guessed correctly and inform them accordingly.
        """
        # Get their current challenge
        challenge_user = User.get(slack_id=user.challenge)
        if not challenge_user:
            message = "Something went wrong while resolving your challenge, please try again later!"
            logger.error(
                f"{event.user} has broken challenge: {user.challenge}, users not in the DB?"
            )
        elif event.message.lower() in challenge_user.all_names:
            message = "Yes! You got it!"
            logger.info(f"{event.user} guessed {user.challenge} correctly.")
        else:
            message = f"Nope, sorry, its: {challenge_user.first_name}"
            logger.info(
                f"{event.user} guessed {user.challenge} incorrectly: {event.message}"
            )

        # Remove challenge and inform user
        user.challenge = None
        user.challenge_datetime = None
        user.save()
        s.SLACK_CLIENT.rtm_send_message(user.slack_channel, message)

    def issue_challenge(self, event: SlackEvent, user: User) -> None:
        """
        The user does not currently have a challenge, issue
        a new challenge if they request one. We rotate through
        all users once randomly per round.
        """
        # See if they want to play the guessing game
        if event.message.startswith(s.PLAY_GAME):
            all_users = user.get_all_valid_users()
            if not all_users:
                logger.error(f"There are no valid users on the Slack server.")
                message = "We couldn't detect any valid users on your Slack server, make sure they have profile pictures!"
                s.SLACK_CLIENT.rtm_send_message(user.slack_channel, message)
                return
            new_challenge = user.get_next_challenge()
            # Get user from DB
            new_challenge_user = User.get(slack_id=new_challenge)
            if new_challenge_user:
                user.challenge = new_challenge
                user.challenge_datetime = datetime.utcnow()
                user.save()
                message = f"Who is this:\n {new_challenge_user.photo_url}"
                s.SLACK_CLIENT.rtm_send_message(user.slack_channel, message)
            else:
                logger.error(
                    f"{event.user} has received broken challenge: {user.challenge}"
                )
                message = "Something went wrong with issuing your new challenge, please try again later!"
                s.SLACK_CLIENT.rtm_send_message(user.slack_channel, message)
        # They are not currently in a round, and they gave us a command we dont understand
        else:
            message = f"I'm not sure what you mean, please try *{s.PLAY_GAME}*."
            logger.info(
                f"{user.slack_id} does not know what they are doing: {event.message}"
            )
            s.SLACK_CLIENT.rtm_send_message(user.slack_channel, message)

    @logger.catch
    def run(self) -> None:
        while True:
            # Blocking, will wait for new events to get added
            # Add a graceful timeout so that we can safely kill thread
            event = None
            try:
                event = s.SLACK_EVENTS_Q.get(timeout=s.QUEUE_TIMEOUT)
            except queue.Empty:
                pass

            if event:
                user = User.get(slack_id=event.user)
                if user and user.challenge:
                    self.resolve_challenge(event, user)
                elif user:
                    self.issue_challenge(event, user)
                else:
                    logger.error(f"Event for a user that doesn't exist in DB: {event}")

            # Check if we need to quit
            if self.stopped():
                break

    def stop(self) -> None:
        self._stop_event.set()

    def stopped(self) -> bool:
        return self._stop_event.is_set()


class ScheduleThread(threading.Thread):
    """
    Use this thread to schedule repetitive tasks, for example
    clearing stale challenges or periodically updating the users.
    """

    def __init__(self) -> None:
        super(ScheduleThread, self).__init__()
        self._stop_event = threading.Event()

    def clear_challenges(self) -> None:
        """
        Delete the challenge if user took too long to respond
        """
        # Get all current challenges
        sql = """
            SELECT
                slack_id, challenge, challenge_datetime
            FROM
                users
            WHERE
                challenge IS NOT NULL;
            """
        challenges = fetch_all_rows_sql(sql)
        for challenge in challenges:
            user = challenge[0]
            challenge_user = challenge[1]
            challenge_time = datetime.strptime(challenge[2], "%Y-%m-%d %H:%M:%S.%f")
            challenge_deadline = challenge_time + timedelta(seconds=s.CHALLENGE_TIMEOUT)
            # This challenge is overdue, we must remove it
            if challenge_deadline <= datetime.utcnow():
                challenge_user = User.get(slack_id=challenge_user)
                user = User.get(slack_id=user)
                if user and challenge_user:
                    user.challenge = None
                    user.challenge_datetime = None
                    user.save()
                    message = f"Sorry, you took to long to respond, it is: {challenge_user.first_name}"
                    logger.info(
                        f"{user.slack_id} took too long to respond, it is: {challenge_user.slack_id}"
                    )
                    s.SLACK_CLIENT.rtm_send_message(user.slack_channel, message)

                else:
                    logger.error(
                        f"Can't clear stale challenges, users dont exist in DB"
                    )

    @logger.catch
    def run(self) -> None:
        # Register the scheduled tasks
        schedule.every(5).seconds.do(self.clear_challenges)
        # Update Slack users data every hour
        schedule.every().hour.do(get_users_from_slack)
        while True:
            # Run all pending tasks every second
            schedule.run_pending()
            time.sleep(1)
            # Check if we need to quit
            if self.stopped():
                break

    def stop(self) -> None:
        self._stop_event.set()

    def stopped(self) -> bool:
        return self._stop_event.is_set()
