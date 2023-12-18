import logging
import os
import sys

LOG_LEVEL = os.environ.get("QA_SERVICE_LOG_LEVEL", "DEBUG")

logging.basicConfig(
    stream=sys.stdout,
    level=LOG_LEVEL,
    format="[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d:%(funcName)s] %(message)s",
)
logger = logging.getLogger(__name__)
logger.propagate = True
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
