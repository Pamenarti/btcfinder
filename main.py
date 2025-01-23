import logging
import sys
from concurrent_log_handler import ConcurrentRotatingFileHandler
from config import LOG_FILE, LOG_FORMAT, LOG_LEVEL, MAX_CPU, DEFAULT_THREAD_COUNT
from address_matcher import AddressMatcher

def setup_logging():
    """Logging ayarlarını yapılandırır"""
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)

    # Dosyaya logla
    file_handler = ConcurrentRotatingFileHandler(
        LOG_FILE,
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(file_handler)

    # Konsola logla
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(console_handler)

def get_thread_count() -> int:
    """Kullanıcıdan thread sayısını alır"""
    while True:
        print("\nSistemde {} CPU çekirdeği bulundu.".format(MAX_CPU))
        print("Önerilen thread sayısı: {}".format(DEFAULT_THREAD_COUNT))
        try:
            thread_count = input("Kullanılacak thread sayısını girin [Enter=Önerilen]: ").strip()
            if not thread_count:
                return DEFAULT_THREAD_COUNT
                
            thread_count = int(thread_count)
            if 1 <= thread_count <= MAX_CPU:
                return thread_count
            else:
                print("Thread sayısı 1 ile {} arasında olmalıdır.".format(MAX_CPU))
        except ValueError:
            print("Geçersiz değer. Lütfen bir sayı girin.")

def get_target_count() -> int:
    """Kullanıcıdan üretilecek cüzdan sayısını alır"""
    while True:
        try:
            count = input("\nKaç adet cüzdan üretilsin? ").strip()
            count = int(count)
            if count > 0:
                return count
            else:
                print("Cüzdan sayısı 0'dan büyük olmalıdır.")
        except ValueError:
            print("Geçersiz değer. Lütfen bir sayı girin.")

def get_log_preference() -> bool:
    """Kullanıcıdan log tercihini alır"""
    while True:
        choice = input("\nÜretilen tüm cüzdanlar kaydedilsin mi? (e/h) [h]: ").strip().lower()
        if choice in ['', 'h', 'n', 'hayır', 'no']:
            return False
        elif choice in ['e', 'y', 'evet', 'yes']:
            print("DİKKAT: Bu seçenek disk kullanımını artıracak ve performansı etkileyebilecektir.")
            confirm = input("Devam etmek istiyor musunuz? (e/h) [h]: ").strip().lower()
            if confirm in ['e', 'y', 'evet', 'yes']:
                return True
            else:
                return False
        print("Geçersiz seçim. 'e' veya 'h' girin.")

def main():
    """Ana program"""
    try:
        setup_logging()
        logging.info("Program başlatılıyor...")
        
        thread_count = get_thread_count()
        target_count = get_target_count()
        log_wallets = get_log_preference()
        
        matcher = AddressMatcher(thread_count, target_count, log_wallets)
        matcher.start_matching()
        
    except KeyboardInterrupt:
        logging.info("Program kullanıcı tarafından durduruldu")
    except Exception as e:
        logging.error("Beklenmeyen hata: {}".format(str(e)), exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 