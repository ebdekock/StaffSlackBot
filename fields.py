import re
from datetime import datetime


class NullEmailField:
    """Email stored as string that can be null. Always lower case."""

    def __get__(self, instance, owner):
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        instance.__dict__[self.name] = None

        if value and type(value) != str:
            raise ValueError(f"Email Field must be string <{self.name}: {value}>")

        if value:
            # See https://emailregex.com/
            value = re.search(
                r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", value, re.IGNORECASE
            )

        if value:
            instance.__dict__[self.name] = value.group(0).lower()

    def __set_name__(self, owner, name):
        self.name = name


class NullDateTimeField:
    """Datetime field that can be null."""

    def __get__(self, instance, owner):
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        if value and type(value) != datetime:
            raise ValueError(f"Field must be datetime <{self.name}: {value}>")
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name


class NullStringField:
    """String field that can be null, defaults lower case with optional upper case"""

    def __init__(self, upper_case=False):
        self.upper_case = upper_case

    def __get__(self, instance, owner):
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        if value and type(value) != str:
            raise ValueError(f"Field must be string or null <{self.name}: {value}>")
        if not value:
            instance.__dict__[self.name] = None
        else:
            instance.__dict__[self.name] = (
                value.lower() if not self.upper_case else value.upper()
            )

    def __set_name__(self, owner, name):
        self.name = name


class StringField:
    """String field, cannot be null, defaults lower case with optional upper case"""

    def __init__(self, upper_case=False):
        self.upper_case = upper_case

    def __get__(self, instance, owner):
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        if not value or type(value) != str:
            raise ValueError(f"Field must be string <{self.name}: {value}>")
        instance.__dict__[self.name] = (
            value.lower() if not self.upper_case else value.upper()
        )

    def __set_name__(self, owner, name):
        self.name = name
