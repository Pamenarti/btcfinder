import os
import psutil
from pathlib import Path

# Sistem kaynak ayarları
PROCESS = psutil.Process()
if hasattr(PROCESS, 'nice'):
    PROCESS.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)

# Dosya yolları
BASE_DIR = Path(__file__).resolve().parent
RICH_ADDRESSES_FILE = os.path.join(BASE_DIR, "rich.txt")
FOUND_ADDRESSES_FILE = os.path.join(BASE_DIR, "found.txt")
WALLET_LOG_FILE = os.path.join(BASE_DIR, "wallets.log")  # Yeni üretilen cüzdanlar için log dosyası

# CPU ayarları
MAX_CPU = os.cpu_count()
DEFAULT_THREAD_COUNT = max(1, MAX_CPU - 1)

# Program ayarları
BATCH_SIZE = 5000  # Her batch'te üretilecek cüzdan sayısı
MAX_RETRIES = 3  # Dosya işlemleri için maksimum deneme sayısı
MEMORY_LIMIT = 0.75  # Maksimum bellek kullanım oranı (75%)

# Logging ayarları
LOG_FILE = os.path.join(BASE_DIR, "btcfinder.log")
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO" 