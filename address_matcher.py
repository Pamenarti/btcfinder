import logging
import time
import queue
import signal
import numpy as np
import cupy as cp
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from typing import List, Tuple, Set
from config import DEFAULT_THREAD_COUNT, BATCH_SIZE
from wallet_generator_gpu import WalletGeneratorGPU
from file_handler import FileHandler

class AddressMatcher:
    def __init__(self, thread_count: int, target_count: int):
        self.file_handler = FileHandler()
        self.wallet_generator = WalletGeneratorGPU()  # GPU destekli generator
        self.thread_count = thread_count
        self.target_count = target_count
        self.total_attempts = 0
        self.start_time = None
        self.is_running = True
        self.max_futures = thread_count * 4  # GPU için daha az thread yeterli
        self.result_queue = queue.Queue(maxsize=10000)  # Kuyruk boyutunu artırdık
        self.progress_interval = max(10000, BATCH_SIZE)  # İlerleme gösterimi aralığını artırdık
        self.batch_multiplier = 4  # GPU için batch boyutunu artırdık
        self.shutdown_event = False
        
        # Rich adresler için GPU belleğinde array
        self.rich_addresses_cpu = np.array(list(self.file_handler.rich_addresses))
        self.rich_addresses_gpu = cp.array(self.rich_addresses_cpu)

        # Ctrl+C sinyalini yakala
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Ctrl+C sinyalini yakalar"""
        if not self.shutdown_event:
            print("\n\nProgram durduruluyor, lütfen bekleyin...")
            self.shutdown_event = True
            self.is_running = False
        else:
            print("\nZorla kapatılıyor!")
            self.display_stats()
            exit(1)

    def optimize_batch_size(self, elapsed_time: float, current_speed: float):
        """Performansa göre batch boyutunu optimize eder"""
        if elapsed_time > 10:
            if current_speed < 50000:  # GPU için eşik değerleri artırdık
                self.batch_multiplier = min(8, self.batch_multiplier * 1.5)
            elif current_speed > 200000:
                self.batch_multiplier = max(2, self.batch_multiplier * 0.8)

    def check_wallet_batch(self) -> List[Tuple[str, str]]:
        """Bir batch cüzdan üretir ve zengin adreslerle eşleşenleri bulur"""
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
        
        # GPU ile hızlı adres kontrolü
        addresses = cp.array([w[0] for w in wallets])
        mask = cp.isin(addresses, self.rich_addresses_gpu)
        if mask.any():
            found_indices = cp.where(mask)[0]
            found_wallets.extend(wallets[i] for i in found_indices.get())
        
        # Sonuçları kuyruğa ekle (her 20 cüzdandan birini göster)
        if not self.shutdown_event:
            for i, wallet in enumerate(wallets):
                if i % 20 == 0:  # GPU için gösterim aralığını artırdık
                    try:
                        self.result_queue.put_nowait(wallet)
                    except queue.Full:
                        pass
        
        self.total_attempts += batch_size
        if self.total_attempts >= self.target_count:
            self.is_running = False
            
        return found_wallets

    def display_progress(self):
        """İlerleme durumunu gösterir"""
        if self.total_attempts % self.progress_interval == 0 and not self.shutdown_event:
            elapsed_time = time.time() - self.start_time
            speed = self.total_attempts / elapsed_time if elapsed_time > 0 else 0
            
            # Batch boyutunu optimize et
            self.optimize_batch_size(elapsed_time, speed)
            
            # İlerleme göster
            print("\rÜretilen: {:,}/{:,} | Hız: {:,.0f} c/s | Batch: {:,} | GPU Bellek: {:.1f}GB".format(
                self.total_attempts, self.target_count, speed, 
                int(BATCH_SIZE * self.batch_multiplier),
                cp.get_default_memory_pool().used_bytes() / 1e9
            ), end="", flush=True)

    def result_printer(self):
        """Ayrı bir thread'de sonuçları yazdırır"""
        last_print_time = time.time()
        while (self.is_running or not self.result_queue.empty()) and not self.shutdown_event:
            try:
                address, private_key = self.result_queue.get(timeout=0.1)
                current_time = time.time()
                if current_time - last_print_time >= 0.1 and not self.shutdown_event:
                    print("\nÜretilen Cüzdan -> Adres: {} | Private Key: {}".format(
                        address, private_key))
                    last_print_time = current_time
                self.display_progress()
            except queue.Empty:
                continue

    def display_stats(self):
        """İstatistikleri gösterir"""
        if self.start_time is None:
            return
            
        elapsed_time = time.time() - self.start_time
        attempts_per_second = self.total_attempts / elapsed_time if elapsed_time > 0 else 0
        
        print("\n\n" + "="*80)
        print("İSTATİSTİKLER")
        print("="*80)
        print("Çalışma Süresi: {:.2f} saniye".format(elapsed_time))
        print("Hedeflenen Cüzdan Sayısı: {:,}".format(self.target_count))
        print("Üretilen Cüzdan Sayısı: {:,}".format(self.total_attempts))
        print("Ortalama Hız: {:,.2f} cüzdan/saniye".format(attempts_per_second))
        print("Son Batch Boyutu: {:,}".format(int(BATCH_SIZE * self.batch_multiplier)))
        print("Kullanılan Thread Sayısı: {}".format(self.thread_count))
        print("GPU Bellek Kullanımı: {:.1f}GB".format(
            cp.get_default_memory_pool().used_bytes() / 1e9))
        print("="*80)

    def start_matching(self):
        """Çoklu thread ile cüzdan üretme ve eşleştirme işlemini başlatır"""
        logging.info("GPU destekli eşleştirme işlemi başlatılıyor... ({} thread ile {} cüzdan üretilecek)".format(
            self.thread_count, self.target_count))
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
                                logging.info("Eşleşen cüzdanlar bulundu!")
                        except Exception as e:
                            logging.error("İşlem hatası: {}".format(str(e)))
                    
                    while len(futures) < self.max_futures and self.is_running and not self.shutdown_event:
                        futures.add(executor.submit(self.check_wallet_batch))
                
                # Temiz kapatma
                self.is_running = False
                for future in futures:
                    future.cancel()
                
                try:
                    printer_future.result(timeout=0.5)
                except:
                    pass
        
        except KeyboardInterrupt:
            print("\nProgram durduruluyor...")
            self.shutdown_event = True
            self.is_running = False
            
            # Tüm işleri iptal et
            for future in futures:
                future.cancel()
        
        except Exception as e:
            logging.error("Beklenmeyen hata: {}".format(str(e)))
            self.shutdown_event = True
            self.is_running = False
        
        finally:
            # GPU belleğini temizle
            try:
                self.rich_addresses_gpu = None
                cp.get_default_memory_pool().free_all_blocks()
            except:
                pass
                
            if not self.shutdown_event:
                print("\nİşlem tamamlandı!")
            self.display_stats() 