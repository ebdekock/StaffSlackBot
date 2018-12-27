import sys

import settings

from utils import get_users_from_slack

# Enable logging.
logger = settings.enable_logging()

# Requirements
assert sys.version_info[0] >= 3, "Require Python 3"
assert settings.SLACK_BOT_TOKEN, "Missing Secret: SLACK_BOT_TOKEN"


if __name__ == "__main__":
    # All we do for now is get all users
    get_users_from_slack()
