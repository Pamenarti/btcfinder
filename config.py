import os
import psutil
from pathlib import Path

# System resource settings
PROCESS = psutil.Process()
if hasattr(PROCESS, 'nice'):
    PROCESS.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)

# File paths
BASE_DIR = Path(__file__).resolve().parent
RICH_ADDRESSES_FILE = os.path.join(BASE_DIR, "rich.txt")
FOUND_ADDRESSES_FILE = os.path.join(BASE_DIR, "found.txt")
WALLET_LOG_FILE = os.path.join(BASE_DIR, "wallets.log")  # Log file for newly generated wallets

# CPU settings
MAX_CPU = os.cpu_count()
DEFAULT_THREAD_COUNT = max(1, MAX_CPU - 1)

# Program settings
BATCH_SIZE = 5000  # Number of wallets to generate in each batch
MAX_RETRIES = 3  # Maximum number of retries for file operations
MEMORY_LIMIT = 0.75  # Maximum memory usage ratio (75%)

# Logging settings
LOG_FILE = os.path.join(BASE_DIR, "btcfinder.log")
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO" 