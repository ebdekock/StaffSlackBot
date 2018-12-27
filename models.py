import sqlite3

from datetime import datetime

import settings

from fields import NullDateTimeField, NullEmailField, NullStringField, StringField
from sql import basic_sql_query, fetch_one_row_sql


class User:
    """
    Base class to manage users. Contains methods
    to save and retrieve users from database.
    """

    # Strict type enforcing on fields
    slack_id = StringField()
    email = NullEmailField()
    full_name = NullStringField()
    pref_name = NullStringField()
    phone = NullStringField()
    photo_url = NullStringField()
    challenge = NullStringField()
    challenge_datetime = NullDateTimeField()

    all_attributes = (
        "slack_id",
        "email",
        "full_name",
        "pref_name",
        "phone",
        "photo_url",
        "challenge",
        "challenge_datetime",
    )

    def __init__(self, **kwargs):
        # Initialise remaining fields with None
        for attribute in self.all_attributes:
            setattr(self, attribute, kwargs.get(attribute, None))

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def _serialise(self):
        """
        Convert user into list of its attributes for saving into
        database. 

        :returns: a list attributes

        """
        return [self[attribute] for attribute in self.all_attributes]

    @classmethod
    def _deserialise(cls, data):
        """
        Convert list of user attributes from database into User object.

        :param data: list of User attributes in same order as User fields
        :returns: a User object

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

    def _update(self, user):
        """
        Update database fields on User objects, it requires that the user
        already exists in the database.

        :param user: serialised

        """
        for attribute in self.all_attributes:
            if self[attribute]:
                user[attribute] = self[attribute]
        # Create list of variables for the update query
        updated_values = user._serialise()
        updated_values.append(user.slack_id)

        # Allows us to create query without worrying about number of attributes on the user
        sql = f"UPDATE users SET {' = ?, '.join(self.all_attributes)} = ? WHERE slack_id = ?"
        basic_sql_query(sql, updated_values)

    def save(self):
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

    def delete(self):
        """
        Delete user from the database if it exists.
        """
        user = User.get(slack_id=self.slack_id)
        if user:
            sql = "DELETE FROM users WHERE slack_id = ?"
            basic_sql_query(sql, (user.slack_id,))

    @staticmethod
    def get(slack_id=None, email=None):
        """
        Retrieve user from database if they exist

        :param slack_id: users slack id (Default value = None)
        :type slack_id: str
        :param email: users email address (Default value = None)
        :type email: str
        :returns: a User object or None
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

    @staticmethod
    def parse_slack_data(data):
        """
        Parse data from Slack API into User object
        See https://api.slack.com/types/user

        :param data: a dictionary from slack api with fields as per above
        :returns: a User object
        """
        profile = data.get("profile")
        user = User(slack_id=data.get("id"))
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

    def __repr__(self):
        return f"{self.__class__.__name__}(" f"{self.email!r}, {self.full_name!r})"
