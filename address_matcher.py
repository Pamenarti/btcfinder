import logging
import time
import queue
import signal
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from typing import List, Tuple, Set
from config import DEFAULT_THREAD_COUNT, BATCH_SIZE, WALLET_LOG_FILE
from wallet_generator import WalletGenerator
from file_handler import FileHandler

class AddressMatcher:
    def __init__(self, thread_count: int, target_count: int, log_wallets: bool = False):
        self.file_handler = FileHandler()
        self.wallet_generator = WalletGenerator()
        self.thread_count = thread_count
        self.target_count = target_count
        self.total_attempts = 0
        self.start_time = None
        self.is_running = True
        self.max_futures = thread_count * 8
        self.result_queue = queue.Queue(maxsize=5000)
        self.progress_interval = max(5000, BATCH_SIZE)
        self.batch_multiplier = 2
        self.shutdown_event = False
        self.log_wallets = log_wallets
        self.wallet_log_buffer = []
        self.wallet_log_buffer_size = 1000  # Write to file every 1000 wallets
        
        # Use numpy array for fast rich address lookup
        self.rich_addresses_array = np.array(list(self.file_handler.rich_addresses))
        self.rich_addresses_set = self.file_handler.rich_addresses

        # Catch Ctrl+C signal
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C signal"""
        if not self.shutdown_event:
            print("\n\nShutting down, please wait...")
            self.shutdown_event = True
            self.is_running = False
        else:
            print("\nForce closing!")
            self.display_stats()
            exit(1)

    def optimize_batch_size(self, elapsed_time: float, current_speed: float):
        """Optimize batch size based on performance"""
        if elapsed_time > 10:
            if current_speed < 10000:
                self.batch_multiplier = min(4, self.batch_multiplier * 1.5)
            elif current_speed > 50000:
                self.batch_multiplier = max(1, self.batch_multiplier * 0.8)

    def _log_wallets_to_file(self, wallets: List[Tuple[str, str]], force: bool = False):
        """Write wallets to log file"""
        if not self.log_wallets:
            return
            
        self.wallet_log_buffer.extend(wallets)
        
        if len(self.wallet_log_buffer) >= self.wallet_log_buffer_size or force:
            try:
                with open(WALLET_LOG_FILE, 'a') as f:
                    for address, private_key in self.wallet_log_buffer:
                        f.write("{}:{}\n".format(address, private_key))
                self.wallet_log_buffer.clear()
            except Exception as e:
                logging.error("Error writing to wallet log file: {}".format(str(e)))

    def check_wallet_batch(self) -> List[Tuple[str, str]]:
        """Generate and check a batch of wallets against rich addresses"""
        if not self.is_running or self.shutdown_event:
            return []
            
        remaining = self.target_count - self.total_attempts
        optimized_batch = int(BATCH_SIZE * self.batch_multiplier)
        batch_size = min(optimized_batch, remaining)
        if batch_size <= 0:
            self.is_running = False
            return []
            
        wallets = self.wallet_generator.generate_wallet_batch(batch_size)
        found_wallets = []
        
        # Fast address checking with numpy
        addresses = np.array([w[0] for w in wallets])
        mask = np.isin(addresses, self.rich_addresses_array)
        if mask.any():
            found_indices = np.where(mask)[0]
            found_wallets.extend(wallets[i] for i in found_indices)
        
        # Log wallets if enabled
        if self.log_wallets:
            self._log_wallets_to_file(wallets)
        
        # Add results to queue (show every 10th wallet)
        if not self.shutdown_event:
            for i, wallet in enumerate(wallets):
                if i % 10 == 0:
                    try:
                        self.result_queue.put_nowait(wallet)
                    except queue.Full:
                        pass
        
        self.total_attempts += batch_size
        if self.total_attempts >= self.target_count:
            self.is_running = False
            
        return found_wallets

    def display_progress(self):
        """Display progress information"""
        if self.total_attempts % self.progress_interval == 0 and not self.shutdown_event:
            elapsed_time = time.time() - self.start_time
            speed = self.total_attempts / elapsed_time if elapsed_time > 0 else 0
            
            # Optimize batch size
            self.optimize_batch_size(elapsed_time, speed)
            
            # Show progress
            status = "\rGenerated: {:,}/{:,} | Speed: {:,.0f} w/s | Batch: {:,}".format(
                self.total_attempts, self.target_count, speed, 
                int(BATCH_SIZE * self.batch_multiplier))
            
            if self.log_wallets:
                status += " | Log: Active"
                
            print(status, end="", flush=True)

    def result_printer(self):
        """Print results in a separate thread"""
        last_print_time = time.time()
        while (self.is_running or not self.result_queue.empty()) and not self.shutdown_event:
            try:
                address, private_key = self.result_queue.get(timeout=0.1)
                current_time = time.time()
                if current_time - last_print_time >= 0.1 and not self.shutdown_event:
                    print("\nGenerated Wallet -> Address: {} | Private Key: {}".format(
                        address, private_key))
                    last_print_time = current_time
                self.display_progress()
            except queue.Empty:
                continue

    def display_stats(self):
        """Display performance statistics"""
        if self.start_time is None:
            return
            
        elapsed_time = time.time() - self.start_time
        attempts_per_second = self.total_attempts / elapsed_time if elapsed_time > 0 else 0
        
        print("\n\n" + "="*80)
        print("STATISTICS")
        print("="*80)
        print("Runtime: {:.2f} seconds".format(elapsed_time))
        print("Target Wallet Count: {:,}".format(self.target_count))
        print("Generated Wallets: {:,}".format(self.total_attempts))
        print("Average Speed: {:,.2f} wallets/second".format(attempts_per_second))
        print("Final Batch Size: {:,}".format(int(BATCH_SIZE * self.batch_multiplier)))
        print("Thread Count: {}".format(self.thread_count))
        print("="*80)

    def start_matching(self):
        """Start wallet generation and matching with multiple threads"""
        logging.info("Starting matching process... ({} threads, {} wallets{})".format(
            self.thread_count, self.target_count, ", wallet logging active" if self.log_wallets else ""))
        self.start_time = time.time()
        
        try:
            with ThreadPoolExecutor(max_workers=self.thread_count + 1) as executor:
                printer_future = executor.submit(self.result_printer)
                futures = set()
                
                while len(futures) < self.max_futures and self.is_running and not self.shutdown_event:
                    futures.add(executor.submit(self.check_wallet_batch))
                
                while futures and self.is_running and not self.shutdown_event:
                    done, not_done = wait(futures, timeout=0.1, return_when=FIRST_COMPLETED)
                    futures = not_done
                    
                    for future in done:
                        try:
                            found_wallets = future.result()
                            if found_wallets:
                                self.file_handler.save_found_wallets_batch(found_wallets)
                                logging.info("Matching wallets found!")
                        except Exception as e:
                            logging.error("Processing error: {}".format(str(e)))
                    
                    while len(futures) < self.max_futures and self.is_running and not self.shutdown_event:
                        futures.add(executor.submit(self.check_wallet_batch))
                
                # Clean shutdown
                self.is_running = False
                for future in futures:
                    future.cancel()
                
                # Write remaining logs
                if self.log_wallets:
                    self._log_wallets_to_file([], force=True)
                
                try:
                    printer_future.result(timeout=0.5)
                except:
                    pass
        
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.shutdown_event = True
            self.is_running = False
            
            # Cancel all tasks
            for future in futures:
                future.cancel()
            
            # Write remaining logs
            if self.log_wallets:
                self._log_wallets_to_file([], force=True)
        
        except Exception as e:
            logging.error("Unexpected error: {}".format(str(e)))
            self.shutdown_event = True
            self.is_running = False
        
        finally:
            if not self.shutdown_event:
                print("\nProcess completed!")
            self.display_stats() 