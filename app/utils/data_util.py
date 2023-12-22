from typing import Any, List
import time
from datetime import datetime
from botocore.exceptions import ClientError

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000


def get_current_milliseconds():
    return int(time.time() * 1000)


def milliseconds_to_human_readable(milliseconds):
    return time.strftime(TIME_FORMAT, time.localtime(milliseconds / 1000))


def custom_client_error(message, operation_name):
    error_response = {
        "Error": {
            "Message": message,
            "Code": "CustomClientError",
        }
    }
    return ClientError(error_response=error_response, operation_name=operation_name)


def assert_not_none(value, msg="Value is None"):
    if value is None:
        raise custom_client_error(msg, "assert_not_none")


def assert_true(state, msg="Invalid state"):
    if state is not True:
        raise custom_client_error(msg, "assert_true")


def now():
    # dynamodb does not support datetime type, so we use isoformat() to convert datetime to string.
    return datetime.now().isoformat()


def get_doc_id(text: str):
    # todo use a better way to generate doc_id
    return text


def is_empty(value: Any):
    return value is None or value == "" or value == [] or value == {}


def del_if_exists(data: dict, keys: List[str]):
    for key in keys:
        if key in data:
            del data[key]


def chunks(long_list, chunk_size):
    for i in range(0, len(long_list), chunk_size):
        yield long_list[i: i + chunk_size]
