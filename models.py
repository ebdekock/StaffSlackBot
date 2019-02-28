import random
from datetime import datetime
from typing import Any, Iterable, List, Optional, Set, Union
from urllib.parse import unquote_plus

# Local
from fields import (
    NullDateTimeField,
    NullEmailField,
    NullStringField,
    StringField,
    BoolField,
)
from sql import basic_sql_query, fetch_all_rows_sql, fetch_one_row_sql


class User:
    """
    Base class to manage users. Contains methods
    to save and retrieve users from database.
    """

    # Strict type enforcing on fields
    slack_id = StringField(upper_case=True)
    slack_channel = NullStringField(upper_case=True)
    email = NullEmailField()
    full_name = NullStringField()
    pref_name = NullStringField()
    phone = NullStringField()
    photo_url = NullStringField()
    challenge = NullStringField(upper_case=True)
    # UTC time
    challenge_datetime = NullDateTimeField()
    # Defaults to true in case face detection is disabled
    can_play_game = BoolField(default=True)

    all_attributes = (
        "slack_id",
        "slack_channel",
        "email",
        "full_name",
        "pref_name",
        "phone",
        "photo_url",
        "challenge",
        "challenge_datetime",
        "can_play_game",
    )

    def __init__(self, **kwargs: Any) -> None:
        # Initialise remaining fields with None, downside is
        # that user has to be created with at least one keyword arg
        for attribute in self.all_attributes:
            setattr(self, attribute, kwargs.get(attribute, None))

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    @property
    def first_name(self) -> Optional[str]:
        return self.full_name.split().pop(0).title() if self.full_name else None

    @property
    def all_names(self) -> Set[str]:
        """
        Return set of names that user could be known as for the guessing
        game.
        """
        names: Set = set()
        if self.full_name:
            names.update(self.full_name.split())
        if self.pref_name:
            names.update(self.pref_name.split())
        return names

    def _serialise(self) -> List[Any]:
        """
        Convert user into list of its attributes for saving into
        database.
        """
        return [self[attribute] for attribute in self.all_attributes]

    @classmethod
    def _deserialise(cls, data: Iterable[Any]) -> "User":
        """
        Convert list of user attributes from database into User object.
        """
        user_data = {}
        for attribute, value in zip(cls.all_attributes, data):
            user_data[attribute] = value
        # Ensure datetime field is parsed correctly
        if user_data["challenge_datetime"]:
            user_data["challenge_datetime"] = datetime.strptime(
                user_data["challenge_datetime"], "%Y-%m-%d %H:%M:%S.%f"
            )
        if user_data["can_play_game"] == 1:
            user_data["can_play_game"] = True
        else:
            user_data["can_play_game"] = False
        return User(**user_data)

    def _update(self, user: "User") -> None:
        """
        Update database fields on User objects, it requires that the user
        already exists in the database.
        """
        for attribute in self.all_attributes:
            user[attribute] = None
            if self[attribute]:
                user[attribute] = self[attribute]
        # Create list of variables for the update query
        updated_values = user._serialise()
        # This is required to specify which user is being updated in the query below
        updated_values.append(user.slack_id)

        # Allows us to create query without worrying about number of attributes on the user
        sql = f"UPDATE users SET {' = ?, '.join(self.all_attributes)} = ? WHERE slack_id = ?"
        basic_sql_query(sql, updated_values)

    def save(self) -> None:
        """
        Save user to the database. If they already exist, we will update
        the values that have changed.
        """
        user = User.get(slack_id=self.slack_id)
        if user:
            self._update(user)
        else:
            # Allows us to create query without worrying about number of attributes on the user
            number_of_attributes = len(self.all_attributes) - 1
            sql = f"INSERT INTO users {self.all_attributes} VALUES(?{', ?' * number_of_attributes})"
            basic_sql_query(sql, self._serialise())

    def delete(self) -> None:
        """
        Delete user from the database if it exists.
        """
        user = User.get(slack_id=self.slack_id)
        if user:
            sql = "DELETE FROM users WHERE slack_id = ?"
            basic_sql_query(sql, (user.slack_id,))

    @staticmethod
    def get(slack_id: str = None, email: str = None) -> Union["User", None]:
        """
        Retrieve user from database if they exist
        """
        # We can search via slack_id or email as they are both
        # unique fields
        search_param = slack_id if slack_id else email
        if not search_param:
            return None
        # Create query based on search parameter
        sql = "SELECT * FROM users WHERE slack_id = ?"
        if not slack_id:
            sql = "SELECT * FROM users WHERE email = ?"
        user = fetch_one_row_sql(sql, (search_param,))

        return User._deserialise(user) if user else None

    @classmethod
    def get_all_users(cls) -> List[Any]:
        """
        Retrieve all users that exist in the database.
        """
        sql = "SELECT * FROM users"
        users = fetch_all_rows_sql(sql)
        return [cls._deserialise(user) for user in users]

    def get_all_valid_users(self) -> List[Any]:
        """
        Retrieve all other users that exist in the database,
        that are valid for the guessing game. Excludes self.
        """
        sql = f"SELECT slack_id FROM users WHERE slack_id NOT LIKE '{self.slack_id}' AND can_play_game = 1"
        users = fetch_all_rows_sql(sql)
        return [user[0] for user in users]

    def get_next_challenge(self) -> str:
        """
        Get the users next random challenge.
        If they have gone through all users, then clear
        their challenges and start a new round.
        """
        all_users = self.get_all_valid_users()
        sql = """
            SELECT
                challenges.challenge
            FROM
                challenges
            INNER JOIN users ON users.slack_id = challenges.slack_id
            WHERE
                users.slack_id = ?;
            """
        current_challenges = fetch_all_rows_sql(sql, (self.slack_id,))
        # Returns list of tuples, need to convert to list
        current_challenges = [challenge[0] for challenge in current_challenges]
        # Exclude users that have already been guessed this round
        available_challenges: Union[set, list] = set(all_users).difference(
            set(current_challenges)
        )
        if not available_challenges:
            # New round - need to reset challenges
            sql = "DELETE FROM challenges WHERE slack_id = ?"
            basic_sql_query(sql, (self.slack_id,))
            available_challenges = all_users[:]
        new_challenge = random.sample(available_challenges, 1).pop()
        # Save new challenge
        sql = f"INSERT INTO challenges (slack_id, challenge) VALUES(?, ?)"
        data = (self.slack_id, new_challenge)
        basic_sql_query(sql, data)
        return new_challenge

    @staticmethod
    def parse_slack_data(data: dict) -> Optional["User"]:
        """
        Parse data from Slack API into User object
        See https://api.slack.com/types/user
        """
        profile = data.get("profile")
        user_id = data.get("id")
        if not user_id or not profile:
            return None
        user = User(slack_id=user_id)
        user.email = profile.get("email")
        # Set this to None string if it doesnt exist
        user.full_name = profile.get("real_name_normalized", "None")
        user.pref_name = profile.get("display_name_normalized")
        user.phone = profile.get("phone")
        profile_image = profile.get("image_192")
        encoded_profile_image = profile_image.split("&d=")[-1]
        user.photo_url = unquote_plus(encoded_profile_image)
        # New or updated user, dont modify challenges
        user.challenge = None
        user.challenge_datetime = None

        return user

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.slack_id!r}, {self.full_name!r})"
