import os
import psutil
from typing import Set, List, Tuple
from config import RICH_ADDRESSES_FILE, FOUND_ADDRESSES_FILE, MAX_RETRIES, MEMORY_LIMIT
import logging

class FileHandler:
    def __init__(self):
        self.rich_addresses = set()
        self.load_rich_addresses()
        self._check_memory_usage()

    def _check_memory_usage(self) -> None:
        """Bellek kullanımını kontrol eder"""
        memory_percent = psutil.Process().memory_percent()
        if memory_percent > MEMORY_LIMIT * 100:
            logging.warning("Yüksek bellek kullanımı: {:.1f}%".format(memory_percent))

    def load_rich_addresses(self) -> None:
        """Zengin adresler dosyasını yükler"""
        try:
            with open(RICH_ADDRESSES_FILE, 'r') as f:
                self.rich_addresses = set(line.strip() for line in f if line.strip())
            logging.info("{} adet zengin adres yüklendi".format(len(self.rich_addresses)))
        except Exception as e:
            logging.error("Zengin adresler yüklenirken hata: {}".format(str(e)))
            raise

    def save_found_wallet(self, address: str, private_key: str) -> None:
        """Bulunan cüzdanı kaydeder"""
        retries = 0
        while retries < MAX_RETRIES:
            try:
                with open(FOUND_ADDRESSES_FILE, 'a') as f:
                    f.write("{}:{}\n".format(address, private_key))
                logging.info("Yeni cüzdan bulundu ve kaydedildi: {}".format(address))
                break
            except Exception as e:
                retries += 1
                logging.error("Cüzdan kaydedilirken hata ({}/{}): {}".format(
                    retries, MAX_RETRIES, str(e)))
                if retries == MAX_RETRIES:
                    raise

    def save_found_wallets_batch(self, wallets: List[Tuple[str, str]]) -> None:
        """Birden fazla bulunan cüzdanı kaydeder"""
        if not wallets:
            return
            
        retries = 0
        while retries < MAX_RETRIES:
            try:
                with open(FOUND_ADDRESSES_FILE, 'a') as f:
                    for address, private_key in wallets:
                        f.write("{}:{}\n".format(address, private_key))
                logging.info("{} adet cüzdan kaydedildi".format(len(wallets)))
                self._check_memory_usage()
                break
            except Exception as e:
                retries += 1
                logging.error("Cüzdanlar kaydedilirken hata ({}/{}): {}".format(
                    retries, MAX_RETRIES, str(e)))
                if retries == MAX_RETRIES:
                    raise

    def is_rich_address(self, address: str) -> bool:
        """Adresin zengin adresler listesinde olup olmadığını kontrol eder"""
        return address in self.rich_addresses 