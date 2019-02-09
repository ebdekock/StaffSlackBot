import sys

import settings as s
from classes import MonitorSlack, ProcessQueue, ScheduleThread
from sql import create_challenges_table
from utils import get_users_from_slack

# Requirements
assert sys.version_info[0] >= 3, "Require Python 3"
assert s.SLACK_BOT_TOKEN, "Missing Secret: SLACK_BOT_TOKEN"

if __name__ == "__main__":
    # Connect to Slack
    s.slack_init()

    # On initial connect, get all users from Slack
    get_users_from_slack()
    # Create table if it doesnt exist
    create_challenges_table()

    # Gets events from Slack
    monitor_slack = MonitorSlack()
    monitor_slack.start()
    # Process events and react if we need to
    process_queue = ProcessQueue()
    process_queue.start()
    # Run scheduled tasks, clear challenges sync users etc.
    schedule_thread = ScheduleThread()
    schedule_thread.start()
