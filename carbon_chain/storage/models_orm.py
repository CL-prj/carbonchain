"""
CarbonChain - ORM Models
=========================
SQLAlchemy ORM models for advanced database features.
"""

from sqlalchemy import Column, Integer, String, BigInteger, LargeBinary, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class BlockORM(Base):
    """Block ORM model"""
    __tablename__ = 'blocks'
    
    height = Column(Integer, primary_key=True)
    hash = Column(LargeBinary(32), unique=True, nullable=False, index=True)
    prev_hash = Column(LargeBinary(32), nullable=False)
    merkle_root = Column(LargeBinary(32), nullable=False)
    timestamp = Column(BigInteger, nullable=False, index=True)
    difficulty = Column(Integer, nullable=False)
    nonce = Column(BigInteger, nullable=False)
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = relationship("TransactionORM", back_populates="block")
    
    # Indexes
    __table_args__ = (
        Index('idx_blocks_timestamp', 'timestamp'),
        Index('idx_blocks_hash', 'hash'),
    )


class TransactionORM(Base):
    """Transaction ORM model"""
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    txid = Column(LargeBinary(32), unique=True, nullable=False, index=True)
    block_height = Column(Integer, nullable=True, index=True)
    tx_type = Column(String(50), nullable=False, index=True)
    timestamp = Column(BigInteger, nullable=False, index=True)
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    block = relationship("BlockORM", back_populates="transactions")
    
    # Indexes
    __table_args__ = (
        Index('idx_transactions_txid', 'txid'),
        Index('idx_transactions_block', 'block_height'),
        Index('idx_transactions_type', 'tx_type'),
        Index('idx_transactions_timestamp', 'timestamp'),
    )


class UTXOORM(Base):
    """UTXO ORM model"""
    __tablename__ = 'utxos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    txid = Column(LargeBinary(32), nullable=False)
    output_index = Column(Integer, nullable=False)
    amount = Column(BigInteger, nullable=False)
    address = Column(String(256), nullable=False, index=True)
    coin_state = Column(String(50), nullable=False, index=True)
    certificate_id = Column(String(50), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Composite primary key
    __table_args__ = (
        Index('idx_utxos_address', 'address'),
        Index('idx_utxos_certificate', 'certificate_id'),
        Index('idx_utxos_state', 'coin_state'),
        Index('idx_utxos_composite', 'txid', 'output_index', unique=True),
    )


class CertificateORM(Base):
    """Certificate ORM model"""
    __tablename__ = 'certificates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    certificate_id = Column(String(50), unique=True, nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)
    vintage = Column(Integer, nullable=False, index=True)
    total_amount = Column(BigInteger, nullable=False)
    assigned_amount = Column(BigInteger, nullable=False, default=0)
    compensated_amount = Column(BigInteger, nullable=False, default=0)
    location = Column(String(256), nullable=True)
    certificate_type = Column(String(50), nullable=False, index=True)
    standard = Column(String(50), nullable=True)
    issue_date = Column(BigInteger, nullable=False)
    metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_certificates_id', 'certificate_id'),
        Index('idx_certificates_project', 'project_id'),
        Index('idx_certificates_type', 'certificate_type'),
        Index('idx_certificates_vintage', 'vintage'),
    )


__all__ = [
    'Base',
    'BlockORM',
    'TransactionORM',
    'UTXOORM',
    'CertificateORM',
]
