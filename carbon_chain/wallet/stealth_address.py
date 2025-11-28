"""
CarbonChain - Stealth Addresses
=================================
Privacy-enhanced addresses per transazioni anonime.

Implementazione completa con ECDH dual-key system.
"""

from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass, field
import secrets
import hashlib

from carbon_chain.domain.crypto_core import (
    generate_keypair,
    compute_sha256,
    generate_random_bytes,
)
from carbon_chain.domain.addressing import (
    public_key_to_address,
)
from carbon_chain.errors import CryptoError
from carbon_chain.logging_setup import get_logger


logger = get_logger("stealth")


# Costanti per secp256k1
SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
SECP256K1_GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
SECP256K1_GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
SECP256K1_A = 0
SECP256K1_B = 7
SECP256K1_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F


class Point:
    """
    Punto su curva ellittica secp256k1.
    """
    def __init__(self, x: Optional[int], y: Optional[int]):
        self.x = x
        self.y = y
    
    def is_infinity(self) -> bool:
        """Check se punto all'infinito"""
        return self.x is None and self.y is None
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Point):
            return False
        return self.x == other.x and self.y == other.y
    
    def __repr__(self) -> str:
        if self.is_infinity():
            return "Point(INF)"
        return f"Point({hex(self.x)[:10]}..., {hex(self.y)[:10]}...)"


class ECC:
    """
    Operazioni su curva ellittica secp256k1.
    """
    
    @staticmethod
    def point_add(p1: Point, p2: Point) -> Point:
        """
        Addizione di punti sulla curva ellittica.
        
        Args:
            p1: Primo punto
            p2: Secondo punto
        
        Returns:
            Point: Somma dei punti
        """
        if p1.is_infinity():
            return p2
        if p2.is_infinity():
            return p1
        
        if p1.x == p2.x:
            if p1.y != p2.y:
                return Point(None, None)  # Infinito
            else:
                # Point doubling
                s = (3 * p1.x * p1.x + SECP256K1_A) * pow(2 * p1.y, -1, SECP256K1_P)
                s %= SECP256K1_P
        else:
            # Point addition
            s = (p2.y - p1.y) * pow(p2.x - p1.x, -1, SECP256K1_P)
            s %= SECP256K1_P
        
        x = (s * s - p1.x - p2.x) % SECP256K1_P
        y = (s * (p1.x - x) - p1.y) % SECP256K1_P
        
        return Point(x, y)
    
    @staticmethod
    def point_multiply(k: int, point: Point) -> Point:
        """
        Moltiplicazione scalare di un punto.
        
        Args:
            k: Scalare
            point: Punto da moltiplicare
        
        Returns:
            Point: k * point
        """
        if k == 0 or point.is_infinity():
            return Point(None, None)
        
        k = k % SECP256K1_N
        result = Point(None, None)
        addend = point
        
        while k:
            if k & 1:
                result = ECC.point_add(result, addend)
            addend = ECC.point_add(addend, addend)
            k >>= 1
        
        return result
    
    @staticmethod
    def compress_point(point: Point) -> bytes:
        """
        Comprimi punto in formato compresso (33 bytes).
        
        Args:
            point: Punto da comprimere
        
        Returns:
            bytes: Punto compresso
        """
        if point.is_infinity():
            return b'\x00' * 33
        
        prefix = b'\x02' if point.y % 2 == 0 else b'\x03'
        return prefix + point.x.to_bytes(32, 'big')
    
    @staticmethod
    def decompress_point(compressed: bytes) -> Point:
        """
        Decomprimi punto da formato compresso.
        
        Args:
            compressed: Punto compresso (33 bytes)
        
        Returns:
            Point: Punto decompresso
        """
        if len(compressed) != 33:
            raise CryptoError("Invalid compressed point length")
        
        prefix = compressed[0]
        x = int.from_bytes(compressed[1:], 'big')
        
        # y^2 = x^3 + 7 (mod p)
        y_squared = (pow(x, 3, SECP256K1_P) + SECP256K1_B) % SECP256K1_P
        y = pow(y_squared, (SECP256K1_P + 1) // 4, SECP256K1_P)
        
        # Scegli y corretto in base al prefix
        if (y % 2 == 0 and prefix == 0x03) or (y % 2 == 1 and prefix == 0x02):
            y = SECP256K1_P - y
        
        return Point(x, y)
    
    @staticmethod
    def get_generator() -> Point:
        """Ottieni generator point G di secp256k1"""
        return Point(SECP256K1_GX, SECP256K1_GY)


def derive_keypair_from_seed(seed: bytes) -> Tuple[int, Point]:
    """
    Deriva keypair da seed.
    
    Args:
        seed: Seed bytes
    
    Returns:
        Tuple[int, Point]: (private_key, public_key)
    """
    # Hash seed per ottenere private key
    private_key = int.from_bytes(
        hashlib.sha256(seed).digest(),
        'big'
    ) % SECP256K1_N
    
    if private_key == 0:
        raise CryptoError("Invalid private key derived")
    
    # Genera public key
    G = ECC.get_generator()
    public_key = ECC.point_multiply(private_key, G)
    
    return private_key, public_key


def compute_ecdh_secret(private_key: int, public_key: Point) -> bytes:
    """
    Calcola shared secret ECDH.
    
    Formula: shared_secret = private_key * public_key
    
    Args:
        private_key: Chiave privata (scalare)
        public_key: Chiave pubblica (punto)
    
    Returns:
        bytes: Shared secret (hash del punto condiviso)
    """
    # ECDH: S = private * public_point
    shared_point = ECC.point_multiply(private_key, public_key)
    
    if shared_point.is_infinity():
        raise CryptoError("ECDH resulted in point at infinity")
    
    # Hash del punto condiviso
    point_bytes = shared_point.x.to_bytes(32, 'big')
    shared_secret = hashlib.sha256(point_bytes).digest()
    
    logger.debug("ECDH shared secret computed")
    
    return shared_secret


@dataclass
class StealthAddress:
    """
    Stealth address per privacy.
    
    Una stealth address permette a mittente di generare
    indirizzo unico per destinatario senza rivelare
    identità destinatario [web:25].
    
    Attributes:
        scan_pubkey: Public key per scanning (compressed)
        spend_pubkey: Public key per spending (compressed)
        address: Derived stealth meta-address
    """
    scan_pubkey: bytes
    spend_pubkey: bytes
    address: str = field(init=False)
    
    def __post_init__(self):
        """Genera address da spend_pubkey"""
        # Converti bytes a Point per derivare address
        spend_point = ECC.decompress_point(self.spend_pubkey)
        self.address = public_key_to_address(self.spend_pubkey)
    
    def __str__(self) -> str:
        return self.address
    
    def to_meta_address(self) -> str:
        """
        Converti a stealth meta-address format.
        
        Returns:
            str: Meta-address (scan_pubkey:spend_pubkey encoded)
        """
        import base64
        meta = base64.b64encode(self.scan_pubkey + self.spend_pubkey).decode()
        return f"stealth:{meta}"
    
    @classmethod
    def from_meta_address(cls, meta_address: str) -> 'StealthAddress':
        """
        Crea da stealth meta-address.
        
        Args:
            meta_address: Meta-address string
        
        Returns:
            StealthAddress: Oggetto stealth address
        """
        import base64
        if not meta_address.startswith("stealth:"):
            raise ValueError("Invalid stealth meta-address format")
        
        data = base64.b64decode(meta_address[8:])
        if len(data) != 66:
            raise ValueError("Invalid stealth meta-address length")
        
        scan_pubkey = data[:33]
        spend_pubkey = data[33:]
        
        return cls(scan_pubkey=scan_pubkey, spend_pubkey=spend_pubkey)


@dataclass
class StealthPayment:
    """
    Stealth payment information.
    
    Contiene informazioni per payment verso stealth address.
    
    Attributes:
        one_time_address: Indirizzo one-time generato
        ephemeral_pubkey: Public key effimera per recipient (compressed)
        amount: Amount da inviare
        tx_hash: Hash della transazione (optional)
    """
    one_time_address: str
    ephemeral_pubkey: bytes
    amount: int
    tx_hash: Optional[str] = None
    
    def __str__(self) -> str:
        return f"StealthPayment(to={self.one_time_address[:16]}..., amount={self.amount})"


class StealthWallet:
    """
    Wallet con supporto stealth addresses.
    
    Implementazione completa con:
    - ECDH key exchange [web:19]
    - Dual-key system (scan + spend) [web:25]
    - Transaction scanning
    """
    
    def __init__(self, seed: Optional[bytes] = None):
        """
        Initialize stealth wallet.
        
        Args:
            seed: Optional seed per deterministic key generation
        """
        if seed is None:
            seed = secrets.token_bytes(32)
        
        # Generate scan keypair
        scan_seed = hashlib.sha256(seed + b"scan").digest()
        self.scan_private, scan_public_point = derive_keypair_from_seed(scan_seed)
        self.scan_public = ECC.compress_point(scan_public_point)
        
        # Generate spend keypair
        spend_seed = hashlib.sha256(seed + b"spend").digest()
        self.spend_private, spend_public_point = derive_keypair_from_seed(spend_seed)
        self.spend_public = ECC.compress_point(spend_public_point)
        
        # Cache per scanning ottimizzato
        self._scanned_payments: Dict[str, StealthPayment] = {}
        
        logger.info(
            "Stealth wallet created",
            extra_data={
                "scan_pub": self.scan_public.hex()[:16],
                "spend_pub": self.spend_public.hex()[:16]
            }
        )
    
    def get_stealth_address(self) -> StealthAddress:
        """
        Get stealth address per receiving.
        
        Returns:
            StealthAddress: Stealth address object con dual keys
        """
        return StealthAddress(
            scan_pubkey=self.scan_public,
            spend_pubkey=self.spend_public
        )
    
    def generate_payment_address(
        self,
        recipient_stealth: StealthAddress,
        amount: int
    ) -> StealthPayment:
        """
        Genera one-time address per payment a recipient.
        
        Usa ECDH per creare shared secret e derivare indirizzo unico.
        
        Formula:
        - Genera ephemeral keypair (r, R) dove R = r*G
        - Shared secret: c = H(r * scan_pubkey)
        - One-time pubkey: P = spend_pubkey + c*G
        - One-time address: address(P)
        
        Args:
            recipient_stealth: Recipient's stealth address
            amount: Amount da inviare
        
        Returns:
            StealthPayment: Payment information con one-time address
        """
        # Genera ephemeral keypair
        ephemeral_seed = generate_random_bytes(32)
        ephemeral_private, ephemeral_public_point = derive_keypair_from_seed(ephemeral_seed)
        ephemeral_public = ECC.compress_point(ephemeral_public_point)
        
        # Decomprimi recipient scan pubkey
        recipient_scan_point = ECC.decompress_point(recipient_stealth.scan_pubkey)
        
        # ECDH: compute shared secret = r * A (dove A = scan_pubkey)
        shared_secret = compute_ecdh_secret(ephemeral_private, recipient_scan_point)
        
        # Converti shared secret a scalare
        c = int.from_bytes(shared_secret, 'big') % SECP256K1_N
        
        # Deriva one-time public key: P = B + c*G
        # (dove B = spend_pubkey)
        recipient_spend_point = ECC.decompress_point(recipient_stealth.spend_pubkey)
        G = ECC.get_generator()
        c_G = ECC.point_multiply(c, G)
        one_time_pubkey = ECC.point_add(recipient_spend_point, c_G)
        
        # Genera address da one-time pubkey
        one_time_pubkey_compressed = ECC.compress_point(one_time_pubkey)
        one_time_address = public_key_to_address(one_time_pubkey_compressed)
        
        payment = StealthPayment(
            one_time_address=one_time_address,
            ephemeral_pubkey=ephemeral_public,
            amount=amount
        )
        
        logger.debug(
            "One-time payment address generated",
            extra_data={
                "address": one_time_address[:16],
                "ephemeral": ephemeral_public.hex()[:16],
                "amount": amount
            }
        )
        
        return payment
    
    def scan_transaction(self, tx_data: dict) -> Optional[Tuple[str, int]]:
        """
        Scanna singola transazione per verificare se appartiene a questo wallet.
        
        Args:
            tx_data: Transaction data con campi:
                - ephemeral_pubkey: bytes (public key effimera)
                - outputs: list di (address, amount)
        
        Returns:
            Optional[Tuple[str, int]]: (one_time_private_key, amount) se trovato, None altrimenti
        """
        try:
            ephemeral_pubkey_bytes = tx_data.get('ephemeral_pubkey')
            outputs = tx_data.get('outputs', [])
            
            if not ephemeral_pubkey_bytes or not outputs:
                return None
            
            # Decomprimi ephemeral pubkey
            ephemeral_pubkey = ECC.decompress_point(ephemeral_pubkey_bytes)
            
            # Calcola shared secret: v * R (dove v = scan_private, R = ephemeral_pubkey)
            shared_secret = compute_ecdh_secret(self.scan_private, ephemeral_pubkey)
            
            # Converti a scalare
            c = int.from_bytes(shared_secret, 'big') % SECP256K1_N
            
            # Deriva expected one-time pubkey: P = B + c*G
            spend_point = ECC.decompress_point(self.spend_public)
            G = ECC.get_generator()
            c_G = ECC.point_multiply(c, G)
            expected_pubkey = ECC.point_add(spend_point, c_G)
            expected_pubkey_compressed = ECC.compress_point(expected_pubkey)
            expected_address = public_key_to_address(expected_pubkey_compressed)
            
            # Verifica se address è negli outputs
            for address, amount in outputs:
                if address == expected_address:
                    # Calcola private key per spendere: p' = b + c
                    one_time_private = (self.spend_private + c) % SECP256K1_N
                    
                    logger.info(
                        "Transaction found for this wallet",
                        extra_data={
                            "address": address[:16],
                            "amount": amount
                        }
                    )
                    
                    # Converti private key a hex string
                    private_key_hex = hex(one_time_private)[2:].zfill(64)
                    
                    return (private_key_hex, amount)
            
            return None
            
        except Exception as e:
            logger.error(f"Error scanning transaction: {e}")
            return None
    
    def scan_transactions(self, transactions: List[dict]) -> List[Dict[str, any]]:
        """
        Scanna lista di transazioni per trovare payments a questo wallet.
        
        Args:
            transactions: Lista di transaction data dicts
        
        Returns:
            list: Lista di found transactions con private keys per spending
        """
        found_transactions = []
        
        logger.info(f"Scanning {len(transactions)} transactions...")
        
        for tx in transactions:
            result = self.scan_transaction(tx)
            if result:
                private_key, amount = result
                found_transactions.append({
                    'tx_hash': tx.get('hash', 'unknown'),
                    'amount': amount,
                    'one_time_private_key': private_key,
                    'ephemeral_pubkey': tx.get('ephemeral_pubkey', b'').hex()
                })
        
        logger.info(
            f"Scanning complete: found {len(found_transactions)} transactions",
            extra_data={"count": len(found_transactions)}
        )
        
        return found_transactions
    
    def export_keys(self) -> dict:
        """
        Esporta chiavi del wallet.
        
        Returns:
            dict: Chiavi pubbliche e private
        """
        return {
            'scan_private': hex(self.scan_private)[2:].zfill(64),
            'scan_public': self.scan_public.hex(),
            'spend_private': hex(self.spend_private)[2:].zfill(64),
            'spend_public': self.spend_public.hex(),
            'stealth_address': self.get_stealth_address().to_meta_address()
        }
    
    @classmethod
    def from_keys(cls, scan_private: str, spend_private: str) -> 'StealthWallet':
        """
        Importa wallet da chiavi private.
        
        Args:
            scan_private: Scan private key (hex)
            spend_private: Spend private key (hex)
        
        Returns:
            StealthWallet: Wallet instance
        """
        wallet = cls.__new__(cls)
        
        # Scan key
        wallet.scan_private = int(scan_private, 16)
        G = ECC.get_generator()
        scan_public_point = ECC.point_multiply(wallet.scan_private, G)
        wallet.scan_public = ECC.compress_point(scan_public_point)
        
        # Spend key
        wallet.spend_private = int(spend_private, 16)
        spend_public_point = ECC.point_multiply(wallet.spend_private, G)
        wallet.spend_public = ECC.compress_point(spend_public_point)
        
        wallet._scanned_payments = {}
        
        logger.info("Stealth wallet imported from keys")
        
        return wallet


# Export pubblici
__all__ = [
    "StealthAddress",
    "StealthWallet",
    "StealthPayment",
    "ECC",
    "Point",
]
