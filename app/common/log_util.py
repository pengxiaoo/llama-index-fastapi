import logging
import sys
import app

ERROR_MSG_USER_NOT_FOUND = "The email address doesn't exist."
system_logger_name = "wikivoyage"
default_formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d:%(funcName)s][%(request_id)s] %(message)s"
)
stream_handler = logging.StreamHandler(stream=sys.stderr)
stream_handler.setLevel("INFO")
stream_handler.setFormatter(default_formatter)
logger = logging.getLogger(system_logger_name)
logger.setLevel("INFO")
logger.propagate = False
logger.addHandler(stream_handler)


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = app.request_id.get("System")
        return True


request_id_filter = RequestIdFilter()
for handler in logger.handlers:
    handler.addFilter(request_id_filter)
