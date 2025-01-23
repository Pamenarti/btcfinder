import logging
import sys
from concurrent_log_handler import ConcurrentRotatingFileHandler
from config import LOG_FILE, LOG_FORMAT, LOG_LEVEL, MAX_CPU, DEFAULT_THREAD_COUNT
from address_matcher import AddressMatcher

def setup_logging():
    """Configure logging settings"""
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)

    # Log to file
    file_handler = ConcurrentRotatingFileHandler(
        LOG_FILE,
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(file_handler)

    # Log to console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(console_handler)

def get_thread_count() -> int:
    """Get number of threads from user"""
    while True:
        print("\nDetected {} CPU cores.".format(MAX_CPU))
        print("Recommended thread count: {}".format(DEFAULT_THREAD_COUNT))
        try:
            thread_count = input("Enter number of threads to use [Enter=Recommended]: ").strip()
            if not thread_count:
                return DEFAULT_THREAD_COUNT
                
            thread_count = int(thread_count)
            if 1 <= thread_count <= MAX_CPU:
                return thread_count
            else:
                print("Thread count must be between 1 and {}.".format(MAX_CPU))
        except ValueError:
            print("Invalid value. Please enter a number.")

def get_target_count() -> int:
    """Get number of wallets to generate from user"""
    while True:
        try:
            count = input("\nHow many wallets to generate? ").strip()
            count = int(count)
            if count > 0:
                return count
            else:
                print("Wallet count must be greater than 0.")
        except ValueError:
            print("Invalid value. Please enter a number.")

def get_log_preference() -> bool:
    """Get wallet logging preference from user"""
    while True:
        choice = input("\nLog all generated wallets? (y/n) [n]: ").strip().lower()
        if choice in ['', 'n', 'no']:
            return False
        elif choice in ['y', 'yes']:
            print("WARNING: This option will increase disk usage and may affect performance.")
            confirm = input("Do you want to continue? (y/n) [n]: ").strip().lower()
            if confirm in ['y', 'yes']:
                return True
            else:
                return False
        print("Invalid choice. Enter 'y' or 'n'.")

def main():
    """Main program"""
    try:
        setup_logging()
        logging.info("Starting program...")
        
        thread_count = get_thread_count()
        target_count = get_target_count()
        log_wallets = get_log_preference()
        
        matcher = AddressMatcher(thread_count, target_count, log_wallets)
        matcher.start_matching()
        
    except KeyboardInterrupt:
        logging.info("Program stopped by user")
    except Exception as e:
        logging.error("Unexpected error: {}".format(str(e)), exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 