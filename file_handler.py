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
        """Check memory usage and warn if too high"""
        memory_percent = psutil.Process().memory_percent()
        if memory_percent > MEMORY_LIMIT * 100:
            logging.warning("High memory usage: {:.1f}%".format(memory_percent))

    def load_rich_addresses(self) -> None:
        """Load rich addresses from file"""
        try:
            with open(RICH_ADDRESSES_FILE, 'r') as f:
                self.rich_addresses = set(line.strip() for line in f if line.strip())
            logging.info("{} rich addresses loaded".format(len(self.rich_addresses)))
        except Exception as e:
            logging.error("Error loading rich addresses: {}".format(str(e)))
            raise

    def save_found_wallet(self, address: str, private_key: str) -> None:
        """Save a found wallet to file"""
        retries = 0
        while retries < MAX_RETRIES:
            try:
                with open(FOUND_ADDRESSES_FILE, 'a') as f:
                    f.write("{}:{}\n".format(address, private_key))
                logging.info("New wallet found and saved: {}".format(address))
                break
            except Exception as e:
                retries += 1
                logging.error("Error saving wallet ({}/{}): {}".format(
                    retries, MAX_RETRIES, str(e)))
                if retries == MAX_RETRIES:
                    raise

    def save_found_wallets_batch(self, wallets: List[Tuple[str, str]]) -> None:
        """Save multiple found wallets to file"""
        if not wallets:
            return
            
        retries = 0
        while retries < MAX_RETRIES:
            try:
                with open(FOUND_ADDRESSES_FILE, 'a') as f:
                    for address, private_key in wallets:
                        f.write("{}:{}\n".format(address, private_key))
                logging.info("{} wallets saved".format(len(wallets)))
                self._check_memory_usage()
                break
            except Exception as e:
                retries += 1
                logging.error("Error saving wallets ({}/{}): {}".format(
                    retries, MAX_RETRIES, str(e)))
                if retries == MAX_RETRIES:
                    raise

    def is_rich_address(self, address: str) -> bool:
        """Check if address is in rich addresses list"""
        return address in self.rich_addresses 