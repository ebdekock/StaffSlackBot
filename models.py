from datetime import datetime
from typing import Any, Iterable, List, Optional, Set, Union

from fields import NullDateTimeField, NullEmailField, NullStringField, StringField
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

    def get_all_other_users(self) -> List[Any]:
        """
        Retrieve all other users that exist in the database.
        """
        sql = f"SELECT slack_id FROM users WHERE slack_id NOT LIKE '{self.slack_id}'"
        users = fetch_all_rows_sql(sql)
        return [user[0] for user in users]

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
        user.photo_url = profile.get("image_192")
        # New or updated user, dont modify challenges
        user.challenge = None
        user.challenge_datetime = None

        return user

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.slack_id!r}, {self.full_name!r})"
