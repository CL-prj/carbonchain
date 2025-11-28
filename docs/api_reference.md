# CarbonChain - API Reference

Complete REST API documentation for CarbonChain blockchain.

---

## Base URL

http://localhost:8000

**Production:**
https://api.carbonchain.io

---

## Authentication

Currently, the API is **open access**. Future versions will support:
- API Keys
- OAuth 2.0
- JWT tokens

---

## Rate Limiting

**Default Limits:**
- Anonymous: 60 requests/minute
- Authenticated: 300 requests/minute

**Headers:**
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640000000

---

## General Endpoints

### Health Check

**GET** `/`

Check API status and version.

**Response:**
{
"name": "CarbonChain API",
"version": "1.0.0",
"status": "running",
"timestamp": 1640000000
}

---

## Blockchain Endpoints

### Get Blockchain Info

**GET** `/blockchain/info`

Get current blockchain statistics.

**Response:**
{
"height": 12345,
"best_block_hash": "000000abc123...",
"difficulty": 1048576,
"total_supply": 1050000000000000,
"total_supply_cco2": 10500000.0,
"mempool_size": 42,
"chain_work": "000000000000000000000000abc123...",
"version": "1.0.0"
}

**Status Codes:**
- `200` - Success
- `500` - Internal server error

---

### Get Block by Height

**GET** `/blockchain/block/height/{height}`

Get block by height number.

**Parameters:**
- `height` (integer) - Block height

**Example:**
curl http://localhost:8000/blockchain/block/height/100

**Response:**
{
"height": 100,
"hash": "000000abc123...",
"prev_hash": "000000def456...",
"merkle_root": "abcdef123456...",
"timestamp": 1640000000,
"difficulty": 4,
"nonce": 12345678,
"transactions": [
{
"txid": "abc123...",
"tx_type": "COINBASE",
"inputs": [],
"outputs": [
{
"amount": 5000000000,
"address": "1ABC..."
}
]
}
]
}

**Status Codes:**
- `200` - Success
- `404` - Block not found
- `400` - Invalid height

---

### Get Block by Hash

**GET** `/blockchain/block/hash/{hash}`

Get block by block hash.

**Parameters:**
- `hash` (string) - Block hash (64 hex characters)

**Example:**
curl http://localhost:8000/blockchain/block/hash/000000abc123...

**Response:** Same as block by height

---

### Get Latest Block

**GET** `/blockchain/latest`

Get the most recent block.

**Response:** Same as block by height

---

### Get Block Range

**GET** `/blockchain/blocks?start={start}&limit={limit}`

Get multiple blocks.

**Query Parameters:**
- `start` (integer) - Starting height (default: 0)
- `limit` (integer) - Number of blocks (default: 10, max: 100)

**Example:**
curl http://localhost:8000/blockchain/blocks?start=100&limit=10

**Response:**
{
"blocks": [...],
"count": 10,
"start": 100,
"end": 109
}

---

## Transaction Endpoints

### Get Transaction

**GET** `/blockchain/transaction/{txid}`

Get transaction details by ID.

**Parameters:**
- `txid` (string) - Transaction ID (64 hex characters)

**Example:**
curl http://localhost:8000/blockchain/transaction/abc123...

**Response:**
{
"txid": "abc123...",
"tx_type": "TRANSFER",
"block_height": 12345,
"confirmations": 6,
"timestamp": 1640000000,
"inputs": [
{
"prev_txid": "def456...",
"prev_index": 0,
"signature": "304402...",
"pubkey": "02abc..."
}
],
"outputs": [
{
"amount": 100000000,
"address": "1ABC...",
"coin_state": "SPENDABLE"
}
],
"fee": 1000,
"size": 250,
"metadata": {}
}

**Status Codes:**
- `200` - Success
- `404` - Transaction not found

---

### Submit Transaction

**POST** `/transaction`

Broadcast a new transaction to the network.

**Request Body:**
{
"tx_type": "TRANSFER",
"inputs": [
{
"prev_txid": "def456...",
"prev_index": 0,
"signature": "304402...",
"pubkey": "02abc..."
}
],
"outputs": [
{
"amount": 100000000,
"address": "1ABC..."
}
],
"metadata": {}
}

**Response:**
{
"txid": "abc123...",
"status": "pending",
"message": "Transaction submitted to mempool"
}

**Status Codes:**
- `201` - Transaction accepted
- `400` - Invalid transaction
- `409` - Double spend detected
- `422` - Validation failed

---

### Get Raw Transaction

**GET** `/blockchain/transaction/{txid}/raw`

Get raw transaction data (hex encoded).

**Response:**
{
"txid": "abc123...",
"hex": "01000000..."
}

---

## Address Endpoints

### Get Address Balance

**GET** `/address/{address}/balance`

Get address balance.

**Parameters:**
- `address` (string) - Blockchain address

**Example:**
curl http://localhost:8000/address/1ABC.../balance

**Response:**
{
"address": "1ABC...",
"balance": 100000000,
"balance_cco2": 1.0,
"received": 500000000,
"sent": 400000000,
"tx_count": 42
}

---

### Get Address UTXOs

**GET** `/address/{address}/utxos`

Get unspent transaction outputs for address.

**Query Parameters:**
- `limit` (integer) - Max UTXOs (default: 100)
- `min_confirmations` (integer) - Minimum confirmations (default: 0)

**Response:**
{
"address": "1ABC...",
"utxos": [
{
"txid": "abc123...",
"index": 0,
"amount": 100000000,
"confirmations": 6,
"coin_state": "SPENDABLE"
}
],
"total_amount": 100000000,
"count": 1
}

---

### Get Address Transactions

**GET** `/address/{address}/transactions`

Get transaction history for address.

**Query Parameters:**
- `offset` (integer) - Pagination offset (default: 0)
- `limit` (integer) - Results per page (default: 50, max: 100)

**Response:**
{
"address": "1ABC...",
"transactions": [
{
"txid": "abc123...",
"block_height": 12345,
"timestamp": 1640000000,
"type": "received",
"amount": 100000000
}
],
"count": 1,
"offset": 0,
"total": 42
}

---

## Certificate Endpoints

### Get Certificate

**GET** `/certificate/{cert_id}`

Get CO₂ certificate details.

**Parameters:**
- `cert_id` (string) - Certificate ID (e.g., CERT-2025-0001)

**Example:**
curl http://localhost:8000/certificate/CERT-2025-0001

**Response:**
{
"certificate_id": "CERT-2025-0001",
"total_amount": 1000000,
"assigned_amount": 500000,
"compensated_amount": 200000,
"remaining": 300000,
"status": "PARTIALLY_COMPENSATED",
"location": "Italy",
"project_id": "PROJ-2025-001",
"issue_date": 1640000000,
"metadata": {
"standard": "VCS",
"type": "Solar Energy",
"vintage": "2025"
}
}

**Status Codes:**
- `200` - Success
- `404` - Certificate not found

---

### List Certificates

**GET** `/certificates`

List all certificates.

**Query Parameters:**
- `status` (string) - Filter by status (ISSUED, PARTIALLY_COMPENSATED, FULLY_COMPENSATED)
- `project_id` (string) - Filter by project
- `offset` (integer) - Pagination offset
- `limit` (integer) - Results per page

**Response:**
{
"certificates": [...],
"count": 10,
"offset": 0,
"total": 145
}

---

### Verify Certificate

**GET** `/certificate/{cert_id}/verify`

Verify certificate authenticity on blockchain.

**Response:**
{
"certificate_id": "CERT-2025-0001",
"verified": true,
"blockchain_height": 12345,
"issue_tx": "abc123...",
"on_chain": true
}

---

## Project Endpoints

### Get Project

**GET** `/project/{project_id}`

Get carbon offset project details.

**Response:**
{
"project_id": "PROJ-2025-001",
"name": "Solar Energy Farm Italy",
"location": "Tuscany, Italy",
"type": "Solar Energy",
"status": "ACTIVE",
"certificates_issued": 45,
"total_co2_offset": 8500000,
"metadata": {
"capacity": "50 MW",
"start_date": "2024-01-01"
}
}

---

### List Projects

**GET** `/projects`

List all carbon offset projects.

**Query Parameters:**
- `status` (string) - Filter by status
- `type` (string) - Filter by type
- `location` (string) - Filter by location

**Response:**
{
"projects": [...],
"count": 10,
"total": 78
}

---

## Mempool Endpoints

### Get Mempool Info

**GET** `/mempool/info`

Get current mempool statistics.

**Response:**
{
"size": 42,
"bytes": 10500,
"usage": 0.01,
"max_mempool": 300000000,
"mempoolminfee": 1000,
"minrelaytxfee": 1000
}

---

### Get Mempool Transactions

**GET** `/mempool/transactions`

List pending transactions in mempool.

**Query Parameters:**
- `limit` (integer) - Max transactions (default: 50)

**Response:**
{
"transactions": [
{
"txid": "abc123...",
"size": 250,
"fee": 5000,
"time": 1640000000
}
],
"count": 42
}

---

## Mining Endpoints

### Get Mining Info

**GET** `/mining/info`

Get mining statistics.

**Response:**
{
"blocks": 12345,
"difficulty": 1048576,
"networkhashps": 1234567890,
"pooledtx": 42,
"chain": "mainnet",
"warnings": ""
}

---

### Submit Block

**POST** `/mining/submit`

Submit a mined block.

**Request Body:**
{
"block_hex": "010000..."
}

**Response:**
{
"accepted": true,
"hash": "000000abc123...",
"height": 12346
}

---

## Network Endpoints

### Get Peer Info

**GET** `/network/peers`

Get connected peer information.

**Response:**
{
"peers": [
{
"id": "peer123",
"address": "192.168.1.100",
"port": 9333,
"version": 1,
"height": 12345,
"ping": 45
}
],
"count": 8
}

---

### Get Network Info

**GET** `/network/info`

Get network statistics.

**Response:**
{
"version": 1,
"protocol_version": 1,
"connections": 8,
"timeoffset": 0,
"difficulty": 1048576,
"testnet": false,
"relayfee": 1000
}

---

## Statistics Endpoints

### Get Statistics

**GET** `/stats`

Get comprehensive blockchain statistics.

**Response:**
{
"blockchain": {
"height": 12345,
"difficulty": 1048576,
"total_supply": 10500000.0,
"average_block_time": 605
},
"network": {
"peers": 8,
"hashrate": 1234567890
},
"mempool": {
"size": 42,
"bytes": 10500
},
"certificates": {
"total": 145,
"active": 120,
"co2_offset": 85000000
}
}

---

## WebSocket API (Future)

### Subscribe to Blocks

**WS** `ws://localhost:8000/ws/blocks`

Real-time block notifications.

**Message:**
{
"type": "block",
"height": 12346,
"hash": "000000abc123...",
"timestamp": 1640000000
}

---

### Subscribe to Transactions

**WS** `ws://localhost:8000/ws/transactions`

Real-time transaction notifications.

**Message:**
{
"type": "transaction",
"txid": "abc123...",
"amount": 100000000
}

---

## Error Responses

### Error Format

{
"error": {
"code": "INVALID_ADDRESS",
"message": "Invalid blockchain address format",
"details": {
"address": "invalid_addr"
}
}
}

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Validation failed |
| `DOUBLE_SPEND` | 409 | Double spend detected |
| `INSUFFICIENT_FUNDS` | 400 | Insufficient balance |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## SDK Examples

### Python

import requests

Get blockchain info
response = requests.get('http://localhost:8000/blockchain/info')
data = response.json()
print(f"Height: {data['height']}")

Get address balance
address = "1ABC..."
response = requests.get(f'http://localhost:8000/address/{address}/balance')
balance = response.json()
print(f"Balance: {balance['balance_cco2']} CCO2")

### JavaScript

// Get blockchain info
fetch('http://localhost:8000/blockchain/info')
.then(response => response.json())
.then(data => console.log('Height:', data.height));

// Submit transaction
const tx = {
tx_type: 'TRANSFER',
inputs: [...],
outputs: [...]
};

fetch('http://localhost:8000/transaction', {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify(tx)
})
.then(response => response.json())
.then(data => console.log('TXID:', data.txid));

### cURL

Get blockchain info
curl http://localhost:8000/blockchain/info

Get block
curl http://localhost:8000/blockchain/block/height/100

Get address balance
curl http://localhost:8000/address/1ABC.../balance

Submit transaction
curl -X POST http://localhost:8000/transaction
-H "Content-Type: application/json"
-d '{"tx_type":"TRANSFER","inputs":[...],"outputs":[...]}'

---

## Pagination

All list endpoints support pagination:

**Query Parameters:**
- `offset` - Starting index (default: 0)
- `limit` - Results per page (default: 50, max: 100)

**Response:**
{
"data": [...],
"pagination": {
"offset": 0,
"limit": 50,
"total": 1234,
"has_more": true
}
}

---

## Versioning

API version is included in the response:

{
"api_version": "v1",
"version": "1.0.0"
}

Future versions will use URL versioning:
https://api.carbonchain.io/v2/blockchain/info

---

**Last Updated:** 2025-11-27  
**API Version:** 1.0.0