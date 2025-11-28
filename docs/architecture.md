# CarbonChain - Architecture Documentation

## Overview

CarbonChain è una blockchain specializzata per la certificazione e compensazione delle emissioni di CO₂. L'architettura è progettata per essere modulare, scalabile e sicura.

---

## System Architecture

┌────────────────────────────────────────────────────────────┐
│                    User Interfaces                         │
├─────────────┬─────────────┬─────────────┬──────────────────┤
│      Web UI │ REST API    │ CLI         │ Mobile App       │
│ (Explorer)  │ (FastAPI)   │ (Typer)     │ (Future)         │
└─────────────┴─────────────┴─────────────┴──────────────────┘
│
┌────────────────────────────────────────────────────────────┐
│                     Service Layer                          │
├─────────────┬─────────────┬─────────────┬──────────────────┤
│ Wallet      │ Certificate │ Compensation│ Mining           │
│ Service     │ Service     │ Service     │ Service          │
├─────────────┼─────────────┼─────────────┼──────────────────┤
│ MultiSig    │ Stealth     │ Project     │ Burn             │
│ Service     │ Service     │ Service     │ Service          │
└─────────────┴─────────────┴─────────────┴──────────────────┘
│
┌────────────────────────────────────────────────────────────┐
│                       Domain Layer                         │
├─────────────┬─────────────┬─────────────┬──────────────────┤
│ Blockchain  │ Mempool     │ UTXO Set    │ Validation       │
├─────────────┼─────────────┼─────────────┼──────────────────┤
│ PoW         │ Genesis     │ Crypto      │ Addressing       │
└─────────────┴─────────────┴─────────────┴──────────────────┘
│
┌────────────────────────────────────────────────────────────┐
│                    Network Layer (P2P)                     │
├─────────────┬─────────────┬─────────────┬──────────────────┤
│ Node        │ Peer        │ Sync        │ Discovery        │
│ Management  │ Manager     │ Protocol    │ Protocol         │
└─────────────┴─────────────┴─────────────┴──────────────────┘
│
┌────────────────────────────────────────────────────────────┐
│                       Storage Layer                        │
├─────────────┬─────────────┬─────────────┬──────────────────┤
│ SQLite      │ UTXO        │ Blocks      │ Certificates     │
│ Database    │ Index       │ Store       │ Store            │
└─────────────┴─────────────┴─────────────┴──────────────────┘

---

## Core Components

### 1. Blockchain Core

**Responsabilità:**
- Gestione della catena di blocchi
- Validazione delle transazioni
- Consensus tramite Proof of Work
- State management

**Moduli principali:**
domain/
├── blockchain.py # Blockchain state machine
├── models.py # Data structures (Block, Transaction)
├── validation.py # Validation rules
├── pow.py # Proof of Work algorithm
└── genesis.py # Genesis block creation

**Caratteristiche:**
- UTXO model (Bitcoin-style)
- Difficulty adjustment ogni 2016 blocchi
- Block time target: 10 minuti
- Max block size: 4 MB

### 2. Transaction System

**Transaction Types:**
1. **COINBASE** - Mining rewards
2. **TRANSFER** - Standard coin transfers
3. **CERTIFICATE** - CO₂ certificate assignment
4. **COMPENSATION** - Certificate compensation

**Transaction Structure:**
{
"txid": "hash(tx_data)",
"tx_type": "TRANSFER",
"inputs": [
{
"prev_txid": "...",
"prev_index": 0,
"signature": "...",
"pubkey": "..."
}
],
"outputs": [
{
"amount": 100000000, # Satoshi
"address": "1ABC...",
"coin_state": "SPENDABLE"
}
],
"timestamp": 1234567890,
"metadata": {}
}

### 3. Certificate System

**Certificate Lifecycle:**
ISSUED → PARTIALLY_COMPENSATED → FULLY_COMPENSATED

**Certificate Structure:**
{
"id": "CERT-2025-0001",
"total_amount": 1000000, # Tons CO₂
"assigned_amount": 500000, # Already assigned
"compensated_amount": 200000, # Already compensated
"location": "Italy",
"project_id": "PROJ-2025-001",
"issue_date": 1234567890,
"metadata": {
"standard": "VCS",
"type": "Solar Energy"
}
}

### 4. UTXO Set

**Design:**
- In-memory index per performance
- Persistent storage in SQLite
- Fast balance lookups
- Efficient coin selection

**Operations:**
add_utxo(txid, index, output)

remove_utxo(txid, index)

get_balance(address)

get_utxos(address)

select_coins(address, amount)

### 5. Proof of Work

**Algorithm:** Scrypt / Argon2id

**Parameters:**
- Initial difficulty: 4 (regtest), 20 (mainnet)
- Target block time: 600 seconds (10 minutes)
- Adjustment period: 2016 blocks (~2 weeks)
- Max adjustment: 4x per period

**Mining Process:**
while True:
block.header.nonce += 1
hash = compute_hash(block.header)
if hash < target:
return block # Valid block found

---

## Network Architecture

### P2P Protocol

**Message Types:**
1. **VERSION** - Handshake and version negotiation
2. **VERACK** - Version acknowledgment
3. **GETBLOCKS** - Request block headers
4. **INV** - Inventory announcement
5. **GETDATA** - Request full data
6. **BLOCK** - Block transmission
7. **TX** - Transaction broadcast
8. **PING/PONG** - Keep-alive

**Connection Flow:**
Node A Node B
| |
|-------- VERSION -------->|
|<------- VERSION ---------|
|-------- VERACK --------->|
|<------- VERACK ----------|
| |
|<------ GETBLOCKS --------|
|-------- INV ------------>|
|<------ GETDATA ----------|
|-------- BLOCK ---------->|

### Blockchain Synchronization

**Phases:**
1. **Initial Block Download (IBD)**
   - Request headers from peers
   - Download blocks in parallel
   - Validate and add to chain

2. **Continuous Sync**
   - Listen for new blocks (INV messages)
   - Request and validate
   - Propagate to other peers

3. **Fork Resolution**
   - Always follow longest valid chain
   - Reorganize if necessary
   - Propagate orphan blocks

---

## Storage Architecture

### Database Schema

**SQLite Tables:**

-- Blocks
CREATE TABLE blocks (
height INTEGER PRIMARY KEY,
hash BLOB UNIQUE NOT NULL,
prev_hash BLOB NOT NULL,
merkle_root BLOB NOT NULL,
timestamp INTEGER NOT NULL,
difficulty INTEGER NOT NULL,
nonce INTEGER NOT NULL,
data BLOB NOT NULL
);

-- Transactions
CREATE TABLE transactions (
txid BLOB PRIMARY KEY,
block_height INTEGER,
tx_type TEXT NOT NULL,
timestamp INTEGER NOT NULL,
data BLOB NOT NULL,
FOREIGN KEY (block_height) REFERENCES blocks(height)
);

-- UTXO Set
CREATE TABLE utxos (
txid BLOB NOT NULL,
output_index INTEGER NOT NULL,
amount INTEGER NOT NULL,
address TEXT NOT NULL,
coin_state TEXT NOT NULL,
certificate_id TEXT,
PRIMARY KEY (txid, output_index)
);

-- Certificates
CREATE TABLE certificates (
certificate_id TEXT PRIMARY KEY,
total_amount INTEGER NOT NULL,
assigned_amount INTEGER NOT NULL,
compensated_amount INTEGER NOT NULL,
location TEXT,
project_id TEXT,
issue_date INTEGER NOT NULL,
metadata TEXT
);

-- Indexes
CREATE INDEX idx_blocks_hash ON blocks(hash);
CREATE INDEX idx_transactions_block ON transactions(block_height);
CREATE INDEX idx_utxos_address ON utxos(address);
CREATE INDEX idx_certificates_project ON certificates(project_id);

### Data Flow

Write Path:
Block → Validation → Database → UTXO Update → Index Update

Read Path:
Query → Index Lookup → Database → Deserialization → Response

---

## Security Architecture

### Cryptography

**Primitives:**
- **Hashing:** SHA-256 (double for block hashes)
- **Signatures:** ECDSA secp256k1
- **Key Derivation:** BIP32 (HD Wallets)
- **Mnemonic:** BIP39 (12/24 words)
- **Address Format:** Base58Check (Bitcoin-compatible)

**Post-Quantum (Phase 3):**
- **Signatures:** Dilithium3 (NIST PQC)
- **KEM:** Kyber768
- **Hybrid mode:** ECDSA + Dilithium

### Validation Rules

**Block Validation:**
1. Hash meets difficulty target
2. Previous hash exists
3. Merkle root matches
4. Timestamp within acceptable range
5. Coinbase transaction valid
6. All transactions valid

**Transaction Validation:**
1. Inputs exist in UTXO set
2. Signatures valid
3. Sum(inputs) ≥ Sum(outputs)
4. No double spends
5. Certificate rules enforced
6. Coin state transitions valid

---

## Advanced Features

### Multi-Signature Wallets

**Scheme:** M-of-N (e.g., 2-of-3)

**PSBT Flow:**
Creator → Sign (1/M) → Sign (2/M) → ... → Sign (M/M) → Broadcast

**Use Cases:**
- Corporate wallets
- Escrow services
- Joint accounts

### Stealth Addresses

**Purpose:** Enhanced privacy

**Protocol:**
1. Recipient publishes scan + spend public keys
2. Sender generates one-time address
3. Only recipient can detect and spend

**Privacy Benefits:**
- Address unlinkability
- Payment confidentiality
- Reduced blockchain analysis

### Lightning Network (Preparation)

**Components:**
- Payment channels
- HTLC (Hash Time-Locked Contracts)
- Channel routing (future)

**Benefits:**
- Instant transactions
- Low fees
- High throughput

---

## Performance Characteristics

### Benchmarks

**Block Processing:**
- Validation: ~10ms per block
- Database write: ~50ms per block
- UTXO update: ~5ms per transaction

**Transaction Processing:**
- Signature verification: ~1ms
- UTXO lookup: ~0.1ms
- Validation: ~1ms total

**Network:**
- Block propagation: <1 second
- Transaction propagation: <500ms
- Peer discovery: ~5 seconds

### Scalability Limits

**Current:**
- Block size: 4 MB
- Transactions per block: ~2000
- TPS: ~3.3 transactions/second

**Optimizations:**
- UTXO set in-memory
- Parallel validation
- Batch database writes
- Bloom filters for SPV

**Future Improvements:**
- SegWit-style witness separation
- Schnorr signatures (aggregation)
- UTXO commitments
- Sharding (Phase 4)

---

## Monitoring & Observability

### Metrics

**Blockchain Metrics:**
- Block height
- Chain work
- UTXO set size
- Mempool size
- Orphan rate

**Network Metrics:**
- Peer count
- Bandwidth usage
- Message latency
- Sync progress

**Performance Metrics:**
- Block validation time
- Transaction throughput
- Database size
- Memory usage

### Logging

**Structured JSON logging:**
{
"timestamp": "2025-11-27T16:00:00Z",
"level": "INFO",
"module": "blockchain",
"event": "block_added",
"data": {
"height": 12345,
"hash": "000000...",
"tx_count": 42,
"validation_time_ms": 15.3
}
}

---

## Deployment Architecture

### Single Node

┌─────────────────────┐
│ CarbonChain Node │
├─────────────────────┤
│ - Blockchain Core │
│ - P2P Network │
│ - REST API │
│ - Web Explorer │
│ - SQLite DB │
└─────────────────────┘

### Multi-Node Cluster

┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Node 1 │<--->│ Node 2 │<--->│ Node 3 │
│ (Mining) │ │ (API Only) │ │ (Archive) │
└─────────────┘ └─────────────┘ └─────────────┘
│ │ │
└────────────────────┴────────────────────┘
│
┌───────────────┐
│ Load Balancer│
└───────────────┘
│
┌───────────────┐
│ Clients │
└───────────────┘

---

## API Architecture

### REST API (FastAPI)

**Endpoints:**
GET / # Health check
GET /blockchain/info # Blockchain statistics
GET /blockchain/block/{id} # Get block
GET /blockchain/transaction/{txid} # Get transaction
GET /address/{address}/balance # Get balance
POST /transaction # Submit transaction
GET /certificate/{id} # Get certificate
GET /mempool/info # Mempool stats

**WebSocket (Future):**
ws://host:port/stream/blocks # Real-time blocks
ws://host:port/stream/mempool # Real-time transactions

---

## Future Enhancements

### Phase 4: Advanced Features

1. **Sharding**
   - Horizontal blockchain partitioning
   - Cross-shard communication
   - Beacon chain coordination

2. **Zero-Knowledge Proofs**
   - Private transactions (zk-SNARKs)
   - Certificate privacy
   - Selective disclosure

3. **Cross-Chain Bridges**
   - Ethereum bridge
   - Binance Smart Chain
   - Polkadot parachain

4. **Governance**
   - On-chain voting
   - Protocol upgrades
   - Parameter adjustments

---

## References

- Bitcoin: https://bitcoin.org/bitcoin.pdf
- Ethereum: https://ethereum.org/en/whitepaper/
- Lightning Network: https://lightning.network/lightning-network-paper.pdf
- BIP32: https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki
- BIP39: https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki

---

**Last Updated:** 2025-11-27  
**Version:** 1.0.0