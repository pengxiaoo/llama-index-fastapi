import logging
import sys

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d:%(funcName)s] %(message)s",
)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))
