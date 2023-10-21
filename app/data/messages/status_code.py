from enum import Enum


class StatusCode(str, Enum):
    """
    "status_code" in the response is a high level descriptive string indicating the status of the request.
    "msg" in the response gives more low level details.
    """

    SUCCEEDED = "SUCCEEDED"

    ERROR_INPUT_FORMAT = "ERROR_INPUT_FORMAT"
    ERROR_ALREADY_EXISTS = "ERROR_ALREADY_EXISTS"
