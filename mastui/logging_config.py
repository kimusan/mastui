import logging
import os
from pathlib import Path

def setup_logging(debug=False):
    """Set up logging to a file if debug mode is enabled."""
    if not debug:
        logging.basicConfig(level=logging.WARNING)
        return None

    config_dir = Path.home() / ".config" / "mastui"
    config_dir.mkdir(parents=True, exist_ok=True)
    log_file = config_dir / "mastui.log"

    # Configure root logger for the app
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename=log_file,
        filemode="w",  # Overwrite the log file on each run
    )

    # Set logging level for noisy libraries to INFO to reduce noise
    logging.getLogger("markdown_it").setLevel(logging.INFO)

    return str(log_file)
