from pydantic import BaseModel
from fastapi import HTTPException
from app.data.messages.status_code import StatusCode


class BaseResponseModel(BaseModel):
    """
    Base class for all the responses
    """

    status_code: StatusCode = StatusCode.SUCCEEDED
    msg: str = "success"

    def __init__(self, **data):
        # only return necessary information to the frontend
        msg = data.get("msg")
        if msg and ": " in msg:
            msg = msg.split(": ")[-1].rstrip(".")
            data["msg"] = msg
        super().__init__(**data)


class CustomHTTPException(HTTPException):
    """
    Base class for all the exceptions
    """

    custom_status_code: str = None

    def __init__(
            self,
            http_status_code: int = 500,
            custom_status_code: str = None,
            detail: str = None,
    ):
        if detail and ": " in detail:
            detail = detail.split(": ")[-1].rstrip(".")
        self.custom_status_code = custom_status_code
        super().__init__(status_code=http_status_code, detail=detail)
