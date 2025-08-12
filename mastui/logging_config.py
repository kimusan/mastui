import logging
import os

def setup_logging():
    """Set up logging to a file."""
    log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mastui.log")
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filename=log_file,
        filemode="w",  # Overwrite the log file on each run
    )
