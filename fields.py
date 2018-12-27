import re

from datetime import datetime


class NullEmailField:
    """Email stored as string that can be null"""

    def __get__(self, instance, owner):
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        instance.__dict__[self.name] = None

        if value and type(value) != str:
            raise ValueError(f"Email Field must be string <{self.name}: {value}>")

        if value:
            # See https://emailregex.com/
            value = re.search(
                r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", value
            )

        if value:
            instance.__dict__[self.name] = value.group(0)

    def __set_name__(self, owner, name):
        self.name = name


class NullDateTimeField:
    """Datetime field that can be null"""

    def __get__(self, instance, owner):
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        if value and type(value) != datetime:
            raise ValueError(f"Field must be datetime <{self.name}: {value}>")
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name


class NullStringField:
    """String field that can be null"""

    def __get__(self, instance, owner):
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        if value and type(value) != str:
            raise ValueError(f"Field must be string or null <{self.name}: {value}>")
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name


class StringField:
    """String field, cannot be null"""

    def __get__(self, instance, owner):
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        if not value or type(value) != str:
            raise ValueError(f"Field must be string <{self.name}: {value}>")
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name