# 🌿 CarbonChain

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)

**Blockchain per Certificazione e Compensazione CO₂**

CarbonChain è una blockchain completa progettata specificamente per la certificazione e compensazione delle emissioni di CO₂. Offre un sistema trasparente, verificabile e immutabile per tracciare certificati di riduzione delle emissioni e compensazioni carbon-neutral.

---

## 📋 Indice

- [✨ Features](#-features)
- [🏗️ Architettura](#️-architettura)
- [🚀 Quick Start](#-quick-start)
- [📦 Installazione](#-installazione)
- [🎯 Uso](#-uso)
- [🧪 Testing](#-testing)
- [🌐 Deployment](#-deployment)
- [📚 Documentazione](#-documentazione)
- [🤝 Contributing](#-contributing)
- [📄 Licenza](#-licenza)

---

## ✨ Features

### 🔐 Core Blockchain (Phase 1)
- **Proof of Work** con Scrypt/Argon2id
- **UTXO Model** con stato completo
- **HD Wallets** (BIP32/BIP39/BIP44)
- **Transaction Types**: COINBASE, TRANSFER, CERTIFICATE, COMPENSATION
- **Genesis Block** configurabile
- **Mempool** con gestione priorità
- **Difficulty Adjustment** automatico
- **Block Validation** strict mode

### 🌐 P2P Network (Phase 2)
- **Peer-to-Peer** networking async
- **Blockchain Sync** automatico
- **Peer Discovery** con bootstrap nodes
- **Message Protocol** completo (VERSION, GETBLOCKS, INV, BLOCK, TX)
- **Connection Management** con reconnection
- **UPnP Support** per NAT traversal

### 🔬 Advanced Features (Phase 3)
- **Multi-Signature Wallets** (M-of-N)
- **PSBT** (Partially Signed Bitcoin Transactions)
- **Stealth Addresses** per privacy
- **Post-Quantum Cryptography** (Dilithium, Kyber)
- **Smart Contracts** (Timelock, Escrow, Conditional)
- **Lightning Network** preparation (Payment Channels, HTLC)

### 🌍 CO₂-Specific
- **Certificate Assignment** on-chain
- **Certificate Verification** con unicità garantita
- **Compensation Tracking** con project linking
- **Certificate Lifecycle** (issued → compensated)
- **Project Registry** immutabile
- **Coin State Tracking** (certified/compensated/spendable)

### 🛠️ Developer Tools
- **REST API** completa (FastAPI)
- **CLI** ricca (Typer + Rich)
- **Web Explorer** integrato
- **Database** SQLite con query ottimizzate
- **Logging** strutturato JSON
- **Monitoring** ready (Prometheus compatible)

---

## 🏗️ Architettura

CarbonChain è organizzato in 5 layer modulari:

### 🌐 API Layer
Interfacce di accesso al sistema:
- **REST API** - Server FastAPI per integrazioni
- **CLI** - Interfaccia a riga di comando (Typer)
- **Explorer** - Interfaccia web per esplorazione blockchain

### ⚙️ Service Layer
Servizi applicativi core:
- **Wallet Service** - Gestione portafogli e chiavi
- **Certificate Service** - Emissione certificati carbon
- **Compensation Service** - Gestione compensazioni
- **Mining Service** - Coordinamento mining
- **MultiSig Service** - Transazioni multi-firma
- **Stealth Service** - Indirizzi stealth per privacy

### 🧩 Domain Layer
Logica blockchain fondamentale:
- **Blockchain** - Catena di blocchi principale
- **Mempool** - Pool transazioni in attesa
- **UTXOSet** - Set UTXO attivi
- **PoW Engine** - Algoritmo Proof of Work
- **Validation** - Validazione transazioni e blocchi
- **Genesis** - Gestione blocco genesis

### 🌍 Network Layer (P2P)
Comunicazione distribuita:
- **Node** - Nodo P2P della rete
- **PeerManager** - Gestione peer connessi
- **Sync** - Sincronizzazione blockchain

### 💾 Storage Layer
Persistenza dati con **SQLite ACID**:
`blocks` | `transactions` | `utxos` | `certificates`

---

## 🚀 Quick Start

### Prerequisiti
- Python 3.10 o superiore
- pip (package installer)
- Git

### Installazione Rapida

Clone repository
git clone https://github.com/CL-prj/carbonchain.git
cd carbonchain

Install dependencies
pip install -r requirements.txt

Initialize node
python -m carbon_chain.cli.main node init

Create wallet
python -m carbon_chain.cli.main wallet create --strength 128

Start mining (testnet)
python -m carbon_chain.cli.main mine start --blocks 10

---

## 📦 Installazione

### Installazione Standard

1. Clone repository
git clone https://github.com/CL-prj/carbonchain.git
cd carbonchain

2. Crea virtual environment (raccomandato)
python -m venv venv
source venv/bin/activate # Linux/Mac

oppure
venv\Scripts\activate # Windows

3. Installa dipendenze
pip install -r requirements.txt

4. Installa in modalità development
pip install -e .

5. Verifica installazione
carbonchain --help

### Installazione Development

Install con dependencies development
pip install -r requirements-dev.txt

Install pre-commit hooks
pre-commit install

Run tests
pytest

Check code quality
black --check .
ruff check .
mypy carbon_chain

### Installazione Docker

Build image
docker build -t carbonchain:latest .

Run container
docker run -d
--name carbonchain-node
-p 9333:9333
-p 8000:8000
-v $(pwd)/data:/app/data
carbonchain:latest

---

## 🎯 Uso

### 1. Inizializzare il Nodo

Initialize blockchain node
carbonchain node init --network mainnet --data-dir ./data

Show node info
carbonchain node info

### 2. Gestione Wallet

Create new wallet (12 words)
carbonchain wallet create --strength 128

Create wallet with 24 words
carbonchain wallet create --strength 256

Recover wallet from mnemonic
carbonchain wallet recover --mnemonic "word1 word2 ... word12"

Check balance
carbonchain wallet balance --index 0

Transfer coins
carbonchain wallet transfer
--to "1RecipientAddress..."
--amount 10.5
--from 0

### 3. Certificati CO₂

Assign certificate
carbonchain cert assign
--id "CERT-2025-001"
--total 1000000
--amount 50000
--location "Italy"
--description "Solar Farm Project"

List certificates
carbonchain cert list

Query certificate
carbonchain query certificate CERT-2025-001

### 4. Mining

Start mining (continuous)
carbonchain mine start --address 0

Mine specific number of blocks
carbonchain mine start --blocks 10 --address 0

Check mining stats
carbonchain mining stats

### 5. Network P2P

Start P2P network node
carbonchain network start --port 9333 --max-peers 128

List connected peers
carbonchain network peers

Start blockchain sync
carbonchain network sync

### 6. Multi-Signature Wallets (Phase 3)

Create 2-of-3 multisig wallet
carbonchain multisig create
--m 2
--n 3
--my-index 0
--name "corporate-wallet"

List multisig wallets
carbonchain multisig list

### 7. Stealth Addresses (Phase 3)

Create stealth wallet
carbonchain stealth create --name "private-wallet"

Scan for stealth payments
carbonchain stealth scan --name "private-wallet" --start 0

### 8. Smart Contracts (Phase 3)

Create timelock contract
carbonchain contract timelock
--to "1Recipient..."
--amount 100
--unlock 1735689600

Create escrow contract
carbonchain contract escrow
--seller "1Seller..."
--amount 500
--timeout 1735689600

---

## 🧪 Testing

### Unit Tests

Run all tests
pytest

Run with coverage
pytest --cov=carbon_chain --cov-report=html

Run specific test file
pytest tests/test_blockchain.py

Run specific test
pytest tests/test_blockchain.py::TestBlockchain::test_add_block

Run with verbose output
pytest -v

Run parallel tests (faster)
pytest -n auto

### Integration Tests

Run integration tests
pytest -m integration

Run Phase 3 integration test
python scripts/test_phase3.py

### Test Coverage Report

Generate HTML coverage report
pytest --cov=carbon_chain --cov-report=html

Open report
open htmlcov/index.html # Mac
xdg-open htmlcov/index.html # Linux
start htmlcov/index.html # Windows

### Benchmarks

Run benchmarks
pytest tests/ --benchmark-only

Post-quantum crypto benchmark
carbonchain pq benchmark --algo dilithium3 --iterations 100

---

## 🌐 Deployment

### Development Environment

Run API server (development)
uvicorn carbon_chain.api.rest_api:app --reload --host 0.0.0.0 --port 8000

Run with auto-reload
make dev

Run CLI
carbonchain node init

### Production Environment

#### 1. Configurazione

Create `.env` file:

Network
CARBONCHAIN_NETWORK=mainnet
CARBONCHAIN_P2P_PORT=9333
CARBONCHAIN_API_PORT=8000

Node
CARBONCHAIN_NODE_NAME="MainNode"
CARBONCHAIN_MINING_ENABLED=true
CARBONCHAIN_MINER_ADDRESS="your_miner_address"

Storage
CARBONCHAIN_DATA_DIR=/var/carbonchain/data
CARBONCHAIN_DB_CACHE_MB=1024

Logging
CARBONCHAIN_LOG_LEVEL=INFO
CARBONCHAIN_LOG_TO_FILE=true
CARBONCHAIN_LOG_DIR=/var/log/carbonchain

Security
CARBONCHAIN_VERIFY_SIGNATURES=true
CARBONCHAIN_BLOCK_VALIDATION_STRICT=true

#### 2. Systemd Service

Create `/etc/systemd/system/carbonchain.service`:

[Unit]
Description=CarbonChain Blockchain Node
After=network.target

[Service]
Type=simple
User=carbonchain
Group=carbonchain
WorkingDirectory=/opt/carbonchain
Environment="PATH=/opt/carbonchain/venv/bin"
ExecStart=/opt/carbonchain/venv/bin/python -m carbon_chain.cli.main node start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

Enable and start:

sudo systemctl daemon-reload
sudo systemctl enable carbonchain
sudo systemctl start carbonchain
sudo systemctl status carbonchain

#### 3. Docker Production

FROM python:3.11-slim

WORKDIR /app

Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

Copy application
COPY . .

Install application
RUN pip install -e .

Create data directory
RUN mkdir -p /app/data

Expose ports
EXPOSE 9333 8000

Run node
CMD ["python", "-m", "carbon_chain.cli.main", "node", "start"]

Build and run:

docker build -t carbonchain:1.0.0 .
docker run -d
--name carbonchain-node
-p 9333:9333
-p 8000:8000
-v carbonchain-data:/app/data
--restart unless-stopped
carbonchain:1.0.0

#### 4. Docker Compose

version: '3.8'

services:
carbonchain-node:
image: carbonchain:1.0.0
container_name: carbonchain-node
ports:
- "9333:9333"
- "8000:8000"
volumes:
- carbonchain-data:/app/data
- carbonchain-logs:/app/logs
environment:
- CARBONCHAIN_NETWORK=mainnet
- CARBONCHAIN_MINING_ENABLED=true
restart: unless-stopped
healthcheck:
test: ["CMD", "curl", "-f", "http://localhost:8000/"]
interval: 30s
timeout: 10s
retries: 3

carbonchain-api:
image: carbonchain:1.0.0
container_name: carbonchain-api
command: uvicorn carbon_chain.api.rest_api:app --host 0.0.0.0 --port 8000
ports:
- "8001:8000"
depends_on:
- carbonchain-node
restart: unless-stopped

volumes:
carbonchain-data:
carbonchain-logs:

Run:

docker-compose up -d
docker-compose logs -f

#### 5. Kubernetes Deployment

apiVersion: apps/v1
kind: Deployment
metadata:
name: carbonchain-node
spec:
replicas: 3
selector:
matchLabels:
app: carbonchain
template:
metadata:
labels:
app: carbonchain
spec:
containers:
- name: carbonchain
image: carbonchain:1.0.0
ports:
- containerPort: 9333
- containerPort: 8000
volumeMounts:
- name: data
mountPath: /app/data
env:
- name: CARBONCHAIN_NETWORK
value: "mainnet"
volumes:
- name: data
persistentVolumeClaim:
claimName: carbonchain-pvc

#### 6. Nginx Reverse Proxy

upstream carbonchain_api {
server 127.0.0.1:8000;
}

server {
listen 80;
server_name api.carbonchain.example.com;

text
location / {
    proxy_pass http://carbonchain_api;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
}

#### 7. Monitoring

Prometheus metrics endpoint
curl http://localhost:8000/metrics

Health check
curl http://localhost:8000/

Node info
curl http://localhost:8000/blockchain/info

---

## 📚 Documentazione

### Struttura Progetto

carbonchain/
├── carbon_chain/ # Main package
│ ├── api/ # REST API
│ ├── cli/ # Command-line interface
│ ├── contracts/ # Smart contracts
│ ├── crypto/ # Post-quantum crypto
│ ├── domain/ # Core blockchain logic
│ ├── layer2/ # Lightning Network
│ ├── network/ # P2P networking
│ ├── services/ # Business logic services
│ ├── storage/ # Database layer
│ └── wallet/ # Wallet implementations
├── tests/ # Unit tests
├── scripts/ # Utility scripts
├── docs/ # Documentation
└── examples/ # Example code

### API Documentation

API documentation disponibile su:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### CLI Documentation

Show all commands
carbonchain --help

Show command help
carbonchain node --help
carbonchain wallet --help
carbonchain cert --help

### Code Documentation

Generate Sphinx documentation:

cd docs
make html
open _build/html/index.html

---

### Development Setup

Clone and setup
git clone https://github.com/CL-prj/carbonchain.git
cd carbonchain
pip install -r requirements-dev.txt
pre-commit install

Create feature branch
git checkout -b feature/amazing-feature

Make changes and test
pytest
black .
ruff check .

Commit and push
git commit -m "Add amazing feature"
git push origin feature/amazing-feature

### Code Style

- **Formatting**: Black (line length 100)
- **Linting**: Ruff + Flake8
- **Type checking**: MyPy
- **Docstrings**: Google style

### Commit Convention

feat: Add new feature
fix: Fix bug
docs: Update documentation
test: Add tests
refactor: Refactor code
chore: Update dependencies

---

## 📊 Performance

### Benchmarks

- **Block validation**: ~10ms per block
- **Transaction validation**: ~1ms per transaction
- **UTXO lookup**: ~0.1ms
- **Mining**: Variable (depends on difficulty)
- **P2P message processing**: ~5ms per message
- **Database write**: ~50ms per block (with fsync)

### Scalability

- **Max block size**: 4 MB
- **Max transactions per block**: ~2000
- **UTXO set size**: Grows linearly with addresses
- **Blockchain size**: ~500 MB per 100k blocks
- **Mempool capacity**: 10,000 transactions

---

## 🔒 Security

### Cryptography

- **Hashing**: SHA-256
- **Signatures**: ECDSA (secp256k1)
- **PoW**: Scrypt / Argon2id
- **Post-Quantum**: Dilithium3, Kyber768 (optional)

### Best Practices

- ✅ Always backup wallet mnemonic
- ✅ Use strong passwords for encrypted wallets
- ✅ Enable 2FA for critical operations
- ✅ Run full node for verification
- ✅ Keep software updated

## 📄 Licenza

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Bitcoin**: Original blockchain inspiration
- **Ethereum**: Smart contract concepts
- **Lightning Network**: Layer 2 scaling
- **NIST**: Post-quantum cryptography standards

---

## 📞 Support

- **Documentation**: https://github.com/CL-prj/carbonchain
- **Issues**: https://github.com/CL-prj/carbonchain/issues
- **Discussions**: https://github.com/CL-prj/carbonchain/discussions


---

Made with ❤️ by CarbonChain Team
