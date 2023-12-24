from typing import Any, List
import time
from datetime import datetime

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000


def get_current_seconds():
    return int(time.time())


def get_current_milliseconds():
    return int(time.time() * 1000)


def milliseconds_to_human_readable(milliseconds):
    return time.strftime(TIME_FORMAT, time.localtime(milliseconds / 1000))


class CustomClientError(ValueError):
    msg: str

    def __init__(self, msg, *args, **kwargs):
        self.msg = msg
        super().__init__(args, kwargs)


def assert_not_none(value, msg=None):
    if value is None:
        msg = "value should not be None" if not msg else msg
        raise CustomClientError(msg)


def assert_true(value, msg=None):
    if value is not True:
        msg = "value should be true" if not msg else msg
        raise CustomClientError(msg)


def now():
    # dynamodb does not support datetime type, so we use isoformat() to convert datetime to string.
    return datetime.now().isoformat()


def get_doc_id(text: str):
    # todo use a better way to generate doc_id
    return text


def is_empty(value: Any):
    return value is None or value == "" or value == [] or value == {}


def not_empty(value: Any):
    return not is_empty(value)


def del_if_exists(data: dict, keys: List[str]):
    for key in keys:
        if key in data:
            del data[key]


def chunks(long_list, chunk_size):
    for i in range(0, len(long_list), chunk_size):
        yield long_list[i: i + chunk_size]
