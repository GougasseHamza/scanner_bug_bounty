import logging
from datetime import datetime

def setup_logger():
    logger = logging.getLogger("BugBountyAutomator")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # Console
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File
    fh = logging.FileHandler("automator.log")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger