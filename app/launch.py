import sys
import time
from multiprocessing import Process
from app.llama_index_server.index_server import main as index_main
from app.main import main as api_main
from app.common.log_util import logger


def start_index_server() -> Process:
    index_server_process = Process(target=index_main)
    index_server_process.daemon = True
    index_server_process.start()
    return index_server_process


def index_server_main() -> Process:
    index_process = start_index_server()
    return index_process


def main():
    index_process = None
    try:
        index_process = index_server_main()
        sleep_time = 30
        logger.info(f"Sleeping for {sleep_time}s to wait for index server, please wait")
        time.sleep(sleep_time)
        logger.info(f"Sleep is done, starting API server")
        api_main()
    except KeyboardInterrupt:
        if index_process:
            index_process.terminate()
        # Re-raise to caller
        raise


if __name__ == "__main__":
    sys.exit(main())
