"""
CarbonChain - Database Storage Layer
======================================
Persistent storage con SQLite.

Security Level: HIGH
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- Block persistence
- Transaction indexing
- UTXO persistence
- Certificate/project tracking
- Query optimization
"""

import sqlite3
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import threading

# Internal imports
from carbon_chain.domain.models import (
    Block,
    Transaction,
    TxOutput,
    UTXOKey,
)
from carbon_chain.errors import (
    DatabaseError,
    DatabaseConnectionError,
    BlockNotFoundError,
    TransactionNotFoundError,
)
from carbon_chain.logging_setup import get_logger
from carbon_chain.config import ChainSettings


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("storage")


# ============================================================================
# DATABASE SCHEMA
# ============================================================================

SCHEMA_VERSION = 1

CREATE_TABLES_SQL = """
-- Blocks table
CREATE TABLE IF NOT EXISTS blocks (
    height INTEGER PRIMARY KEY,
    hash TEXT UNIQUE NOT NULL,
    version INTEGER NOT NULL,
    previous_hash TEXT NOT NULL,
    merkle_root TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    difficulty INTEGER NOT NULL,
    nonce INTEGER NOT NULL,
    tx_count INTEGER NOT NULL,
    block_data BLOB NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_blocks_hash ON blocks(hash);
CREATE INDEX IF NOT EXISTS idx_blocks_timestamp ON blocks(timestamp);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    txid TEXT PRIMARY KEY,
    block_height INTEGER NOT NULL,
    tx_type INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    input_count INTEGER NOT NULL,
    output_count INTEGER NOT NULL,
    tx_data BLOB NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (block_height) REFERENCES blocks(height)
);

CREATE INDEX IF NOT EXISTS idx_tx_block_height ON transactions(block_height);
CREATE INDEX IF NOT EXISTS idx_tx_type ON transactions(tx_type);
CREATE INDEX IF NOT EXISTS idx_tx_timestamp ON transactions(timestamp);

-- UTXO table (current unspent outputs)
CREATE TABLE IF NOT EXISTS utxos (
    txid TEXT NOT NULL,
    output_index INTEGER NOT NULL,
    address TEXT NOT NULL,
    amount INTEGER NOT NULL,
    is_certified INTEGER NOT NULL DEFAULT 0,
    is_compensated INTEGER NOT NULL DEFAULT 0,
    is_burned INTEGER NOT NULL DEFAULT 0,
    certificate_id TEXT,
    certificate_hash TEXT,
    output_data BLOB NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (txid, output_index)
);

CREATE INDEX IF NOT EXISTS idx_utxo_address ON utxos(address);
CREATE INDEX IF NOT EXISTS idx_utxo_certified ON utxos(is_certified);
CREATE INDEX IF NOT EXISTS idx_utxo_compensated ON utxos(is_compensated);
CREATE INDEX IF NOT EXISTS idx_utxo_cert_id ON utxos(certificate_id);

-- Certificates table
CREATE TABLE IF NOT EXISTS certificates (
    certificate_id TEXT PRIMARY KEY,
    certificate_hash TEXT UNIQUE NOT NULL,
    total_kg INTEGER NOT NULL,
    issued_kg INTEGER NOT NULL DEFAULT 0,
    compensated_kg INTEGER NOT NULL DEFAULT 0,
    first_txid TEXT NOT NULL,
    first_block INTEGER NOT NULL,
    metadata TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cert_hash ON certificates(certificate_hash);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,
    project_type TEXT,
    location TEXT,
    organization TEXT,
    total_kg_compensated INTEGER NOT NULL DEFAULT 0,
    first_txid TEXT NOT NULL,
    first_block INTEGER NOT NULL,
    metadata TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_project_type ON projects(project_type);

-- Project certificates (many-to-many)
CREATE TABLE IF NOT EXISTS project_certificates (
    project_id TEXT NOT NULL,
    certificate_id TEXT NOT NULL,
    PRIMARY KEY (project_id, certificate_id),
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (certificate_id) REFERENCES certificates(certificate_id)
);

-- Metadata table
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);

-- Insert schema version
INSERT OR REPLACE INTO metadata (key, value, updated_at) 
VALUES ('schema_version', '1', strftime('%s', 'now'));
"""


# ============================================================================
# DATABASE CLASS
# ============================================================================

class BlockchainDatabase:
    """
    Database SQLite per blockchain persistence.
    
    Thread-safe con connection pooling.
    
    Attributes:
        db_path: Path database file
        config: Chain configuration
    
    Examples:
        >>> db = BlockchainDatabase(Path("blockchain.db"), config)
        >>> db.save_block(block)
        >>> loaded = db.load_block(0)
    """
    
    def __init__(self, db_path: Path, config: ChainSettings):
        self.db_path = db_path
        self.config = config
        
        # Thread-local storage per connections
        self._local = threading.local()
        
        # Initialize database
        self._initialize_database()
        
        logger.info(
            "Database initialized",
            extra_data={"db_path": str(db_path)}
        )
    
    def _get_connection(self) -> sqlite3.Connection:
        """Ottieni connection thread-local"""
        if not hasattr(self._local, 'connection'):
            try:
                self._local.connection = sqlite3.connect(
                    str(self.db_path),
                    check_same_thread=False,
                    timeout=30.0
                )
                # Enable foreign keys
                self._local.connection.execute("PRAGMA foreign_keys = ON")
                # WAL mode for better concurrency
                self._local.connection.execute("PRAGMA journal_mode = WAL")
            except sqlite3.Error as e:
                raise DatabaseConnectionError(
                    f"Failed to connect to database: {e}",
                    code="DB_CONNECTION_FAILED"
                )
        
        return self._local.connection
    
    def _initialize_database(self) -> None:
        """Inizializza database con schema"""
        try:
            conn = self._get_connection()
            conn.executescript(CREATE_TABLES_SQL)
            conn.commit()
            
            logger.info("Database schema initialized")
        
        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to initialize database: {e}",
                code="DB_INIT_FAILED"
            )
    
    # ========================================================================
    # BLOCK OPERATIONS
    # ========================================================================
    
    def save_block(self, block: Block) -> None:
        """
        Salva blocco su database.
        
        Args:
            block: Block da salvare
        
        Raises:
            DatabaseError: Se salvataggio fallisce
        
        Examples:
            >>> db.save_block(block)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Serialize block
            block_data = json.dumps(block.to_dict()).encode('utf-8')
            block_hash = block.compute_block_hash()
            
            # Insert block
            cursor.execute("""
                INSERT INTO blocks (
                    height, hash, version, previous_hash, merkle_root,
                    timestamp, difficulty, nonce, tx_count, block_data, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                block.header.height,
                block_hash,
                block.header.version,
                block.header.previous_hash,
                block.header.merkle_root.hex(),
                block.header.timestamp,
                block.header.difficulty,
                block.header.nonce,
                len(block.transactions),
                block_data,
                int(time.time())
            ))
            
            # Save transactions
            for tx in block.transactions:
                self._save_transaction(cursor, tx, block.header.height)
            
            # Update UTXO set
            self._update_utxos(cursor, block)
            
            # Update certificates/projects
            self._update_certificates_and_projects(cursor, block)
            
            conn.commit()
            
            logger.debug(
                f"Block saved to database",
                extra_data={
                    "height": block.header.height,
                    "hash": block_hash[:16] + "..."
                }
            )
        
        except sqlite3.Error as e:
            conn.rollback()
            raise DatabaseError(
                f"Failed to save block: {e}",
                code="BLOCK_SAVE_FAILED"
            )
    
    def load_block(self, height: int) -> Optional[Block]:
        """
        Carica blocco da database.
        
        Args:
            height: Block height
        
        Returns:
            Block: Blocco caricato, o None se non trovato
        
        Examples:
            >>> block = db.load_block(0)  # Genesis
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT block_data FROM blocks WHERE height = ?
            """, (height,))
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Deserialize
            block_dict = json.loads(row[0])
            block = Block.from_dict(block_dict)
            
            return block
        
        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to load block: {e}",
                code="BLOCK_LOAD_FAILED"
            )
    
    def load_all_blocks(self) -> List[Block]:
        """
        Carica tutti i blocchi (ordinati per height).
        
        Returns:
            List[Block]: Lista blocchi
        
        Examples:
            >>> blocks = db.load_all_blocks()
            >>> len(blocks)
            100
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT block_data FROM blocks ORDER BY height ASC
            """)
            
            blocks = []
            for row in cursor.fetchall():
                block_dict = json.loads(row[0])
                block = Block.from_dict(block_dict)
                blocks.append(block)
            
            return blocks
        
        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to load blocks: {e}",
                code="BLOCKS_LOAD_FAILED"
            )
    
    def get_block_count(self) -> int:
        """
        Ottieni numero blocchi.
        
        Returns:
            int: Count
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM blocks")
            return cursor.fetchone()[0]
        
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to count blocks: {e}")
    
    def get_latest_block_height(self) -> Optional[int]:
        """
        Ottieni height ultimo blocco.
        
        Returns:
            int: Height, o None se DB vuoto
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT MAX(height) FROM blocks")
            result = cursor.fetchone()[0]
            
            return result
        
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to get latest height: {e}")
    
    # ========================================================================
    # TRANSACTION OPERATIONS
    # ========================================================================
    
    def _save_transaction(
        self,
        cursor: sqlite3.Cursor,
        tx: Transaction,
        block_height: int
    ) -> None:
        """Salva transazione (internal)"""
        import time
        
        tx_data = json.dumps(tx.to_dict()).encode('utf-8')
        txid = tx.compute_txid()
        
        cursor.execute("""
            INSERT INTO transactions (
                txid, block_height, tx_type, timestamp,
                input_count, output_count, tx_data, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            txid,
            block_height,
            tx.tx_type.value,
            tx.timestamp,
            len(tx.inputs),
            len(tx.outputs),
            tx_data,
            int(time.time())
        ))
    
    def load_transaction(self, txid: str) -> Optional[Transaction]:
        """
        Carica transazione.
        
        Args:
            txid: Transaction ID
        
        Returns:
            Transaction: Tx caricata
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT tx_data FROM transactions WHERE txid = ?
            """, (txid,))
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            tx_dict = json.loads(row[0])
            return Transaction.from_dict(tx_dict)
        
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to load transaction: {e}")
    
    def get_transactions_by_address(
        self,
        address: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Ottieni transazioni per address.
        
        Args:
            address: Address da query
            limit: Max risultati
        
        Returns:
            List[dict]: Lista tx info
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Query UTXO per address
            cursor.execute("""
                SELECT txid, output_index, amount, is_certified, is_compensated
                FROM utxos 
                WHERE address = ?
                LIMIT ?
            """, (address, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "txid": row[0],
                    "output_index": row[1],
                    "amount": row[2],
                    "is_certified": bool(row[3]),
                    "is_compensated": bool(row[4])
                })
            
            return results
        
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to query transactions: {e}")
    
    # ========================================================================
    # UTXO OPERATIONS
    # ========================================================================
    
    def _update_utxos(self, cursor: sqlite3.Cursor, block: Block) -> None:
        """Update UTXO set con blocco (internal)"""
        import time
        
        for tx in block.transactions:
            txid = tx.compute_txid()
            
            # Rimuovi input spesi (se non COINBASE)
            if not tx.is_coinbase():
                for inp in tx.inputs:
                    cursor.execute("""
                        DELETE FROM utxos 
                        WHERE txid = ? AND output_index = ?
                    """, (inp.prev_txid, inp.prev_output_index))
            
            # Aggiungi output (se non BURN)
            if not tx.is_burn():
                for idx, output in enumerate(tx.outputs):
                    output_data = json.dumps(output.to_dict()).encode('utf-8')
                    
                    cursor.execute("""
                        INSERT INTO utxos (
                            txid, output_index, address, amount,
                            is_certified, is_compensated, is_burned,
                            certificate_id, certificate_hash,
                            output_data, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        txid,
                        idx,
                        output.address,
                        output.amount,
                        1 if output.is_certified else 0,
                        1 if output.is_compensated else 0,
                        1 if output.is_burned else 0,
                        output.certificate_id,
                        output.certificate_hash.hex() if output.certificate_hash else None,
                        output_data,
                        int(time.time())
                    ))
    
    def load_utxos(self) -> Dict[UTXOKey, TxOutput]:
        """
        Carica tutti gli UTXO da database.
        
        Returns:
            dict: Mapping UTXOKey → TxOutput
        
        Examples:
            >>> utxos = db.load_utxos()
            >>> len(utxos)
            1000
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT txid, output_index, output_data FROM utxos")
            
            utxos = {}
            for row in cursor.fetchall():
                txid, output_index, output_data = row
                
                output_dict = json.loads(output_data)
                output = TxOutput.from_dict(output_dict)
                
                utxo_key = UTXOKey(txid, output_index)
                utxos[utxo_key] = output
            
            return utxos
        
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to load UTXOs: {e}")
    
    def get_utxos_by_address(self, address: str) -> List[Dict]:
        """
        Ottieni UTXO per address.
        
        Args:
            address: Address
        
        Returns:
            List[dict]: Lista UTXO
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT txid, output_index, amount, is_certified, is_compensated
                FROM utxos
                WHERE address = ?
            """, (address,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "txid": row[0],
                    "output_index": row[1],
                    "amount": row[2],
                    "is_certified": bool(row[3]),
                    "is_compensated": bool(row[4])
                })
            
            return results
        
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to query UTXOs: {e}")
    
    # ========================================================================
    # CERTIFICATE/PROJECT OPERATIONS
    # ========================================================================
    
    def _update_certificates_and_projects(
        self,
        cursor: sqlite3.Cursor,
        block: Block
    ) -> None:
        """Update certificates e projects (internal)"""
        import time
        
        for tx in block.transactions:
            txid = tx.compute_txid()
            
            # Update certificates
            if tx.is_certificate_assignment():
                for output in tx.outputs:
                    if not output.is_certified:
                        continue
                    
                    # Upsert certificate
                    cursor.execute("""
                        INSERT INTO certificates (
                            certificate_id, certificate_hash, total_kg,
                            issued_kg, compensated_kg, first_txid, first_block,
                            metadata, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(certificate_id) DO UPDATE SET
                            issued_kg = issued_kg + ?,
                            compensated_kg = compensated_kg + ?
                    """, (
                        output.certificate_id,
                        output.certificate_hash.hex(),
                        output.certificate_total_kg,
                        output.amount,
                        output.amount if output.is_compensated else 0,
                        txid,
                        block.header.height,
                        json.dumps(output.certificate_metadata or {}),
                        int(time.time()),
                        output.amount,
                        output.amount if output.is_compensated else 0
                    ))
            
            # Update projects
            if tx.is_compensation():
                for output in tx.outputs:
                    if not output.is_compensated:
                        continue
                    
                    metadata = output.compensation_metadata or {}
                    
                    # Upsert project
                    cursor.execute("""
                        INSERT INTO projects (
                            project_id, project_name, project_type, location,
                            organization, total_kg_compensated, first_txid,
                            first_block, metadata, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(project_id) DO UPDATE SET
                            total_kg_compensated = total_kg_compensated + ?
                    """, (
                        output.compensation_project_id,
                        metadata.get("project_name", output.compensation_project_id),
                        metadata.get("project_type", "unknown"),
                        metadata.get("location", ""),
                        metadata.get("organization", ""),
                        output.amount,
                        txid,
                        block.header.height,
                        json.dumps(metadata),
                        int(time.time()),
                        output.amount
                    ))
                    
                    # Link project-certificate
                    cursor.execute("""
                        INSERT OR IGNORE INTO project_certificates (
                            project_id, certificate_id
                        ) VALUES (?, ?)
                    """, (output.compensation_project_id, output.certificate_id))
    
    def get_certificate_info(self, cert_id: str) -> Optional[Dict]:
        """Ottieni info certificato"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT certificate_id, certificate_hash, total_kg,
                       issued_kg, compensated_kg, first_txid, first_block, metadata
                FROM certificates
                WHERE certificate_id = ?
            """, (cert_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                "certificate_id": row[0],
                "certificate_hash": row[1],
                "total_kg": row[2],
                "issued_kg": row[3],
                "compensated_kg": row[4],
                "first_txid": row[5],
                "first_block": row[6],
                "metadata": json.loads(row[7])
            }
        
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to get certificate: {e}")
    
    def get_project_info(self, project_id: str) -> Optional[Dict]:
        """Ottieni info progetto"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT project_id, project_name, project_type, location,
                       organization, total_kg_compensated, first_txid, first_block, metadata
                FROM projects
                WHERE project_id = ?
            """, (project_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Get certificates
            cursor.execute("""
                SELECT certificate_id FROM project_certificates
                WHERE project_id = ?
            """, (project_id,))
            
            certificates = [r[0] for r in cursor.fetchall()]
            
            return {
                "project_id": row[0],
                "project_name": row[1],
                "project_type": row[2],
                "location": row[3],
                "organization": row[4],
                "total_kg_compensated": row[5],
                "first_txid": row[6],
                "first_block": row[7],
                "metadata": json.loads(row[8]),
                "certificates_used": certificates
            }
        
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to get project: {e}")
    
    # ========================================================================
    # UTILITY
    # ========================================================================
    
    def close(self) -> None:
        """Chiudi database connections"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')
        
        logger.info("Database closed")
    
    def vacuum(self) -> None:
        """Ottimizza database (VACUUM)"""
        try:
            conn = self._get_connection()
            conn.execute("VACUUM")
            logger.info("Database vacuumed")
        except sqlite3.Error as e:
            logger.error(f"Vacuum failed: {e}")


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "BlockchainDatabase",
]
