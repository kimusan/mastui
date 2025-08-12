import logging
import os

def setup_logging(debug=False):
    """Set up logging to a file."""
    log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mastui.log")
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filename=log_file,
        filemode="w",  # Overwrite the log file on each run
    )
