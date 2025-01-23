import hashlib
import random
from typing import Tuple, List
import coincurve
from base58 import b58encode_check

class WalletGenerator:
    @staticmethod
    def generate_private_key() -> str:
        """Generate a random private key"""
        return ''.join(['%x' % random.randrange(16) for _ in range(64)])

    @staticmethod
    def private_to_public(private_key: str) -> bytes:
        """Convert private key to public key"""
        private_key_bytes = bytes.fromhex(private_key)
        public_key = coincurve.PublicKey.from_valid_secret(private_key_bytes).format(compressed=True)
        return public_key

    @staticmethod
    def public_to_address(public_key: bytes) -> str:
        """Convert public key to Bitcoin address"""
        sha256_hash = hashlib.sha256(public_key).digest()
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
        version = b'\x00'  # mainnet
        vh160 = version + ripemd160_hash
        return b58encode_check(vh160).decode('utf-8')

    @classmethod
    def generate_wallet(cls) -> Tuple[str, str]:
        """Generate a new Bitcoin wallet pair (address, private_key)"""
        private_key = cls.generate_private_key()
        public_key = cls.private_to_public(private_key)
        address = cls.public_to_address(public_key)
        return address, private_key

    @classmethod
    def generate_wallet_batch(cls, batch_size: int) -> List[Tuple[str, str]]:
        """Generate multiple Bitcoin wallet pairs"""
        return [cls.generate_wallet() for _ in range(batch_size)] 