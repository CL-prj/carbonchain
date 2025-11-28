# CarbonChain - Certificate Specification

Technical specification for CO₂ certificate system on CarbonChain blockchain.

---

## Table of Contents

1. [Overview](#overview)
2. [Certificate Types](#certificate-types)
3. [Certificate Lifecycle](#certificate-lifecycle)
4. [Data Structure](#data-structure)
5. [Issuance Process](#issuance-process)
6. [Assignment & Compensation](#assignment--compensation)
7. [Verification Standards](#verification-standards)
8. [Smart Contract Integration](#smart-contract-integration)
9. [API Reference](#api-reference)

---

## Overview

CarbonChain certificates represent verified CO₂ offsets recorded immutably on the blockchain. Each certificate is:

✅ **Unique** - One-time issuance per project/vintage  
✅ **Verifiable** - Cryptographically signed by issuer  
✅ **Traceable** - Complete on-chain history  
✅ **Fractional** - Divisible into smaller units  
✅ **Transparent** - Publicly auditable  

### Key Concepts

**Certificate:** Digital representation of CO₂ offset
- Issued by certified projects
- Measured in tons CO₂ equivalent (tCO₂e)
- Linked to specific project and vintage

**Coin State:** Status of CCO₂ coins
- `SPENDABLE` - Normal tradable coins
- `CERTIFIED` - Assigned to certificate (locked)
- `COMPENSATED` - Permanently burned (offset claimed)

---

## Certificate Types

### 1. Renewable Energy Certificates (RECs)

**Sources:**
- Solar farms
- Wind energy
- Hydroelectric power
- Geothermal energy

**Standards:**
- I-REC Standard
- TIGR (The International REC Standard)

**Example:**
{
"type": "RENEWABLE_ENERGY",
"subtype": "SOLAR",
"capacity_mw": 50,
"annual_generation_mwh": 87600
}

### 2. Forest Conservation Certificates

**Sources:**
- REDD+ projects (Reducing Emissions from Deforestation)
- Reforestation
- Afforestation
- Forest management

**Standards:**
- VCS (Verified Carbon Standard)
- CCB (Climate, Community & Biodiversity)

**Example:**
{
"type": "FOREST_CONSERVATION",
"subtype": "REDD_PLUS",
"area_hectares": 10000,
"co2_sequestration_annual_tons": 50000
}

### 3. Carbon Capture & Storage (CCS)

**Sources:**
- Direct air capture (DAC)
- Biochar
- Ocean alkalinity enhancement
- Mineral carbonation

**Standards:**
- Puro.earth Standard
- Gold Standard for CCS

**Example:**
{
"type": "CARBON_CAPTURE",
"subtype": "DIRECT_AIR_CAPTURE",
"capture_capacity_annual_tons": 5000,
"storage_method": "GEOLOGICAL"
}

### 4. Energy Efficiency Certificates

**Sources:**
- Building retrofits
- Industrial process improvements
- Transportation efficiency

**Standards:**
- ISO 50001 Energy Management
- LEED Certification

### 5. Methane Reduction Certificates

**Sources:**
- Landfill gas capture
- Agricultural methane reduction
- Coal mine methane capture

**Standards:**
- CAR (Climate Action Reserve)
- ACR (American Carbon Registry)

---

## Certificate Lifecycle

┌──────────────┐
│ PROJECT │
│ DEVELOPMENT │
└──────┬───────┘
│
↓
┌──────────────┐
│ VERIFICATION │ ← Third-party auditor
│ & APPROVAL │ (VCS, Gold Standard)
└──────┬───────┘
│
↓
┌──────────────┐
│ ISSUANCE │ ← On-chain certificate creation
│ (ISSUED) │ Transaction: CERTIFICATE type
└──────┬───────┘
│
↓
┌──────────────┐
│ ASSIGNMENT │ ← Coins locked to certificate
│ (CERTIFIED) │ Coin state: SPENDABLE → CERTIFIED
└──────┬───────┘
│
↓
┌──────────────┐
│ COMPENSATION │ ← CO₂ offset claimed
│(COMPENSATED) │ Coin state: CERTIFIED → COMPENSATED
└──────┬───────┘ Coins permanently burned
│
↓
┌──────────────┐
│ RETIRED │ ← Certificate fully compensated
│ (FINAL) │ No further assignments possible
└──────────────┘

### State Transitions

| From | To | Action | Reversible |
|------|----|----|-----------|
| - | `ISSUED` | Certificate created | No |
| `ISSUED` | `PARTIALLY_COMPENSATED` | First assignment | No |
| `PARTIALLY_COMPENSATED` | `PARTIALLY_COMPENSATED` | Additional assignments | No |
| `PARTIALLY_COMPENSATED` | `FULLY_COMPENSATED` | Final assignment | No |
| `FULLY_COMPENSATED` | - | Terminal state | No |

---

## Data Structure

### Certificate On-Chain Format

@dataclass
class Certificate:
"""
CO₂ Certificate stored on blockchain.
"""
# Identification
certificate_id: str # Format: CERT-YYYY-NNNN
project_id: str # Format: PROJ-YYYY-NNNN
vintage: int # Year of CO₂ reduction

text
# Amounts (in satoshi: 1 CCO₂ = 1 ton CO₂)
total_amount: int                # Total certificate size
assigned_amount: int             # Amount already assigned to coins
compensated_amount: int          # Amount already compensated

# Metadata
certificate_type: CertificateType
location: str                    # Country/region
issue_date: int                  # Unix timestamp
expiry_date: Optional[int]       # Optional expiration

# Issuer Information
issuer_address: str              # Blockchain address of issuer
issuer_signature: bytes          # Digital signature
issuer_pubkey: bytes             # Public key for verification

# Verification
standard: str                    # VCS, Gold Standard, etc.
registry_id: Optional[str]       # External registry ID
verification_document: str       # IPFS hash of PDF

# Additional Data
metadata: Dict[str, Any]         # Flexible metadata

def to_dict(self) -> Dict:
    """Serialize to dictionary"""
    return {
        "certificate_id": self.certificate_id,
        "project_id": self.project_id,
        "vintage": self.vintage,
        "total_amount": self.total_amount,
        "assigned_amount": self.assigned_amount,
        "compensated_amount": self.compensated_amount,
        "type": self.certificate_type.value,
        "location": self.location,
        "issue_date": self.issue_date,
        "standard": self.standard,
        "metadata": self.metadata
    }
### Certificate Transaction Format

{
"txid": "abc123...",
"tx_type": "CERTIFICATE",
"version": 1,
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
"amount": 100000000000,
"address": "1ProjectAddress...",
"coin_state": "SPENDABLE"
}
],
"metadata": {
"certificate": {
"certificate_id": "CERT-2025-0001",
"project_id": "PROJ-2025-001",
"vintage": 2025,
"total_amount": 1000000000000,
"certificate_type": "RENEWABLE_ENERGY",
"location": "Italy",
"standard": "VCS",
"issuer": "1IssuerAddress...",
"verification_doc": "ipfs://Qm...",
"metadata": {
"capacity_mw": 50,
"technology": "Solar PV",
"commissioning_date": "2024-06-01"
}
}
},
"timestamp": 1640000000
}

---

## Issuance Process

### Step 1: Project Registration

**Off-Chain:**
1. Project developer completes verification
2. Third-party auditor validates CO₂ reduction
3. Certificate issued by registry (VCS, Gold Standard)

**On-Chain Preparation:**
Generate certificate ID
cert_id = f"CERT-{year}-{sequential_number:04d}"

Prepare certificate data
certificate = Certificate(
certificate_id=cert_id,
project_id="PROJ-2025-001",
vintage=2025,
total_amount=1_000_000_000_000, # 10,000 tons
certificate_type=CertificateType.RENEWABLE_ENERGY,
location="Italy",
standard="VCS",
issuer_address=issuer_address,
verification_document="ipfs://Qm..."
)

### Step 2: On-Chain Issuance

Create certificate transaction
carbonchain certificate issue
--id CERT-2025-0001
--project PROJ-2025-001
--amount 10000
--type RENEWABLE_ENERGY
--location Italy
--standard VCS
--verification-doc ipfs://Qm...
--issuer-key issuer.pem

**Transaction Details:**
- Type: `CERTIFICATE`
- Creates new coins equal to certificate amount
- Coins initially in `SPENDABLE` state
- Certificate metadata in transaction metadata
- Signed by authorized issuer

### Step 3: Verification

Verify certificate on blockchain
carbonchain certificate verify CERT-2025-0001

Output:
✅ Certificate Verified
═══════════════════════════════════════
Certificate ID: CERT-2025-0001
Status: ISSUED
Total Amount: 10,000 tons CO₂
Issuer: 1IssuerAddress...
Signature: Valid ✓
Block Height: 12345
Confirmations: 6
---

## Assignment & Compensation

### Certificate Assignment

**Process:**
1. Holder sends CCO₂ to certificate address
2. Coins change state: `SPENDABLE` → `CERTIFIED`
3. Certificate's `assigned_amount` increases
4. Coins locked (cannot be spent normally)

Assign coins to certificate
carbonchain certificate assign
--id CERT-2025-0001
--amount 1000
--from-address 1MyAddress...

Transaction created:
- Inputs: Regular CCO₂ coins
- Outputs: Coins with CERTIFIED state
- Metadata: certificate_id reference
**On-Chain:**
{
"tx_type": "TRANSFER",
"outputs": [
{
"amount": 100000000000,
"address": "1CertificateAddress...",
"coin_state": "CERTIFIED",
"certificate_id": "CERT-2025-0001"
}
]
}

### Compensation (Burning)

**Process:**
1. Certified coins are spent to burn address
2. Coins change state: `CERTIFIED` → `COMPENSATED`
3. Certificate's `compensated_amount` increases
4. CO₂ offset officially claimed

Compensate certificate (burn coins)
carbonchain certificate compensate
--id CERT-2025-0001
--amount 1000
--claim-name "My Company"

**Burn Address:**
1CCO2BurnAddressXXXXXXXXXXXYs9mBD

**Verification:**
Verify compensation
carbonchain certificate check CERT-2025-0001

Output:
Certificate: CERT-2025-0001
Total: 10,000 tons CO₂
Assigned: 5,000 tons CO₂ (50%)
Compensated: 2,000 tons CO₂ (20%)
Remaining: 8,000 tons CO₂ (80%)
Status: PARTIALLY_COMPENSATED
---

## Verification Standards

### Supported Standards

#### 1. VCS (Verified Carbon Standard)

**Registry:** Verra  
**Website:** https://verra.org  
**Requirements:**
- Independent third-party verification
- Additionality demonstration
- Permanence guarantees
- No double-counting

**Integration:**
{
"standard": "VCS",
"registry_id": "VCS-1234",
"methodology": "VM0007",
"verification_body": "RINA"
}

#### 2. Gold Standard

**Registry:** Gold Standard Foundation  
**Website:** https://goldstandard.org  
**Requirements:**
- Sustainable Development Goals (SDGs) alignment
- Stakeholder consultation
- Monitoring plan

#### 3. CAR (Climate Action Reserve)

**Focus:** North American projects  
**Standards:** Rigorous accounting protocols

#### 4. ACR (American Carbon Registry)

**First:** Voluntary offset registry (1996)  
**Coverage:** Global projects

### Certificate Validation Rules

def validate_certificate(cert: Certificate) -> bool:
"""Validate certificate meets requirements"""

text
# 1. ID format check
if not re.match(r'^CERT-\d{4}-\d{4,}$', cert.certificate_id):
    return False

# 2. Amount consistency
if cert.assigned_amount > cert.total_amount:
    return False
if cert.compensated_amount > cert.assigned_amount:
    return False

# 3. Issuer signature verification
if not verify_signature(
    cert.issuer_pubkey,
    cert.issuer_signature,
    cert.to_bytes()
):
    return False

# 4. Issuer authorization check
if not is_authorized_issuer(cert.issuer_address):
    return False

# 5. Standard recognition
if cert.standard not in RECOGNIZED_STANDARDS:
    return False

# 6. Expiry check (if applicable)
if cert.expiry_date and time.time() > cert.expiry_date:
    return False

return True
---

## Smart Contract Integration

### Timelock Certificates

**Use Case:** Gradual release of certificates

Create timelock certificate
contract = TimelockContract(
certificate_id="CERT-2025-0001",
total_amount=10_000_000_000_000,
release_schedule=[
(1640000000, 2_000_000_000_000), # 20% at date 1
(1650000000, 3_000_000_000_000), # 30% at date 2
(1660000000, 5_000_000_000_000), # 50% at date 3
]
)

### Conditional Release

**Use Case:** Performance-based certificates

Release certificate only if conditions met
contract = ConditionalContract(
certificate_id="CERT-2025-0001",
conditions={
"min_energy_generated_mwh": 100000,
"verified_by": "1AuditorAddress...",
"verification_deadline": 1670000000
}
)

### Escrow for Certificate Trading

Escrow for secure certificate sale
escrow = EscrowContract(
seller="1SellerAddress...",
buyer="1BuyerAddress...",
certificate_id="CERT-2025-0001",
amount=1_000_000_000_000,
price=500_000_000_000, # 5000 CCO₂
deadline=1650000000
)

---

## API Reference

### Get Certificate

GET /certificate/{cert_id}

**Response:**
{
"certificate_id": "CERT-2025-0001",
"project_id": "PROJ-2025-001",
"vintage": 2025,
"total_amount": 10000000000000,
"assigned_amount": 5000000000000,
"compensated_amount": 2000000000000,
"remaining": 8000000000000,
"status": "PARTIALLY_COMPENSATED",
"type": "RENEWABLE_ENERGY",
"location": "Italy",
"standard": "VCS",
"issue_date": 1640000000,
"issuer": "1IssuerAddress...",
"verified": true
}

### List Certificates

GET /certificates?status=ACTIVE&project=PROJ-2025-001

### Verify Certificate

GET /certificate/{cert_id}/verify

### Certificate History

GET /certificate/{cert_id}/history

**Response:**
{
"certificate_id": "CERT-2025-0001",
"history": [
{
"date": 1640000000,
"action": "ISSUED",
"amount": 10000000000000,
"txid": "abc123..."
},
{
"date": 1645000000,
"action": "ASSIGNED",
"amount": 3000000000000,
"txid": "def456..."
},
{
"date": 1650000000,
"action": "COMPENSATED",
"amount": 2000000000000,
"txid": "ghi789..."
}
]
}

---

## Appendix

### Certificate ID Format

CERT-YYYY-NNNN
│ │ │
│ │ └─ Sequential number (4+ digits)
│ └────── Year of issuance
└─────────── Certificate prefix

**Examples:**
- `CERT-2025-0001` - First certificate of 2025
- `CERT-2025-1234` - Certificate #1234 of 2025

### Project ID Format

PROJ-YYYY-NNNN

### Standards References

- **VCS:** https://verra.org/programs/verified-carbon-standard/
- **Gold Standard:** https://www.goldstandard.org/
- **CAR:** https://www.climateactionreserve.org/
- **ACR:** https://acrcarbon.org/

---

**Last Updated:** 2025-11-27  
**Specification Version:** 1.0.0