# CarbonChain - Wallet Guide

Complete guide to creating, managing, and securing your CarbonChain wallet.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Wallet Types](#wallet-types)
3. [Creating a Wallet](#creating-a-wallet)
4. [Backup & Recovery](#backup--recovery)
5. [Sending & Receiving](#sending--receiving)
6. [Security Best Practices](#security-best-practices)
7. [Advanced Features](#advanced-features)
8. [Troubleshooting](#troubleshooting)

---

## Introduction

A CarbonChain wallet allows you to:
- **Store** CCO₂ coins securely
- **Send** payments to other addresses
- **Receive** payments from anyone
- **Manage** CO₂ certificates
- **View** transaction history

### Wallet Types

| Type | Security | Ease of Use | Best For |
|------|----------|-------------|----------|
| **CLI Wallet** | ⭐⭐⭐⭐⭐ | ⭐⭐ | Advanced users |
| **Web Wallet** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Quick access |
| **Mobile Wallet** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Daily use |
| **Hardware Wallet** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Large amounts |
| **Paper Wallet** | ⭐⭐⭐⭐⭐ | ⭐ | Cold storage |

---

## Creating a Wallet

### CLI Wallet (Recommended)

#### 1. Install CarbonChain

Install from source
git clone https://github.com/carbonchain/carbonchain.git
cd carbonchain
pip install -e .

Verify installation
carbonchain --version

#### 2. Create New Wallet

Create wallet with 12-word mnemonic (128-bit security)
carbonchain wallet create --strength 128

Or 24-word mnemonic (256-bit security - recommended)
carbonchain wallet create --strength 256

**Output:**
🔐 Creating new HD wallet...

⚠️ CRITICAL: BACKUP YOUR MNEMONIC PHRASE!

Write down these 24 words in order and store them safely:

abandon 2. ability 3. able 4. about

above 6. absent 7. absorb 8. abstract

absurd 10. abuse 11. access 12. accident

account 14. accuse 15. achieve 16. acid

acoustic 18. acquire 19. across 20. act

action 22. actor 23. actress 24. actual

⚠️ Anyone with this phrase can access your funds!
⚠️ Never share it or store it digitally!

✅ Wallet created successfully!

Your first address (m/44'/0'/0'/0/0):
1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa

Wallet saved to: ~/.carbonchain/wallets/default.json

#### 3. Important First Steps

⚠️ IMMEDIATELY backup mnemonic on paper
Write it down 2-3 times and store in different secure locations
Verify backup (optional but recommended)
carbonchain wallet recover --mnemonic "your 24 words here" --verify-only

Check wallet info
carbonchain wallet info

### Recover Existing Wallet

Recover from mnemonic
carbonchain wallet recover --mnemonic "word1 word2 ... word24"

Recover with custom derivation path
carbonchain wallet recover
--mnemonic "word1 word2 ... word24"
--path "m/44'/0'/0'/0/0"

Verify without saving
carbonchain wallet recover --mnemonic "..." --verify-only

---

## Wallet Management

### List Wallets

List all wallets
carbonchain wallet list

Output:
Available Wallets:
═══════════════════════════════════════
1. default (3 addresses)
2. savings (1 address)
3. mining (10 addresses)
### Generate New Addresses

Generate next address (HD wallet)
carbonchain wallet address --new

Generate specific index
carbonchain wallet address --index 5

List all addresses
carbonchain wallet addresses

### Check Balance

Check total wallet balance
carbonchain wallet balance

Output:
Wallet Balance
═══════════════════════════════════════
Total Balance: 1,234.56789000 CCO₂
Spendable: 1,200.00000000 CCO₂
Certified: 34.56789000 CCO₂
Compensated: 0.00000000 CCO₂
Check specific address
carbonchain wallet balance --address 1A1zP1eP...

Check by index
carbonchain wallet balance --index 0

---

## Sending & Receiving

### Receive Payments

Get your address
carbonchain wallet address

Output:
1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
Generate QR code (if qrcode library installed)
carbonchain wallet qr --address 1A1zP1eP...

**Share with sender:**
- Copy address and send via secure channel
- Or share QR code for mobile wallets
- **Never** share your private key or mnemonic!

### Send Payments

#### Basic Transfer

Send 10 CCO₂ to address
carbonchain wallet transfer
--to 1RecipientAddress...
--amount 10.0

Send from specific address index
carbonchain wallet transfer
--to 1RecipientAddress...
--amount 10.0
--from 0

Custom fee
carbonchain wallet transfer
--to 1RecipientAddress...
--amount 10.0
--fee 0.001

**Output:**
📤 Sending Transaction
═══════════════════════════════════════
From: 1YourAddress...
To: 1RecipientAddress...
Amount: 10.00000000 CCO₂
Fee: 0.00010000 CCO₂
Total: 10.00010000 CCO₂

Confirm transaction? [y/N]: y

✅ Transaction sent!
TXID: abc123def456...

View on explorer:
https://explorer.carbonchain.io/tx/abc123def456...

#### Send to Multiple Addresses

Batch payment
carbonchain wallet transfer
--to 1Address1:5.0,1Address2:3.0,1Address3:2.0

#### Send All (Sweep)

Send entire balance (minus fee)
carbonchain wallet transfer
--to 1RecipientAddress...
--amount all

### Transaction History

View transaction history
carbonchain wallet history

Last N transactions
carbonchain wallet history --limit 10

Specific date range
carbonchain wallet history
--from 2025-01-01
--to 2025-12-31

Export to CSV
carbonchain wallet history --export transactions.csv

---

## Backup & Recovery

### Mnemonic Backup (Critical)

**⚠️ Your mnemonic is the ONLY way to recover your funds!**

#### Best Practices:

1. **Write it down** - Never store digitally
✅ Paper (2-3 copies)
✅ Metal backup plate (fireproof)
❌ Computer file
❌ Phone photo
❌ Cloud storage
❌ Email

2. **Store securely**
✅ Safe deposit box
✅ Home safe
✅ Fireproof bag
✅ Multiple locations
❌ Desk drawer
❌ Wallet (physical)

3. **Test recovery**
Verify backup works (doesn't save)
carbonchain wallet recover
--mnemonic "your words"
--verify-only

### Export Wallet

Export encrypted wallet file
carbonchain wallet export --output backup.json --encrypt

Enter password when prompted
Store backup.json safely (encrypted with password)
Export specific addresses (watch-only)
carbonchain wallet export
--addresses-only
--output addresses.txt

### Import Wallet

Import encrypted wallet
carbonchain wallet import --file backup.json

Enter password when prompted
---

## Security Best Practices

### Password Security

Set strong password for wallet encryption
carbonchain wallet encrypt

Requirements:
- At least 12 characters
- Mix of uppercase, lowercase, numbers, symbols
- Unique (not used elsewhere)
Change password
carbonchain wallet change-password

### Two-Factor Authentication (CLI)

Enable 2FA for transactions
carbonchain wallet config --2fa enable

Requires confirmation code for:
- Sending transactions > 100 CCO₂
- Wallet exports
- Password changes
### Cold Storage

**For large amounts (> 10,000 CCO₂):**

1. **Air-gapped computer**
   - Never connected to internet
   - Used only for signing transactions

2. **Create offline wallet**
On air-gapped machine
carbonchain wallet create --strength 256 --offline

3. **Sign transactions offline**
On online machine: create unsigned tx
carbonchain wallet transfer
--to 1Recipient...
--amount 1000
--create-unsigned > unsigned.tx

Transfer unsigned.tx to offline machine (USB)
On offline machine: sign
carbonchain wallet sign --file unsigned.tx > signed.tx

Transfer signed.tx back to online machine
On online machine: broadcast
carbonchain wallet broadcast --file signed.tx

### Security Checklist

- [ ] ✅ Mnemonic backed up on paper (2+ copies)
- [ ] ✅ Strong password set
- [ ] ✅ Wallet file encrypted
- [ ] ✅ Regular balance checks
- [ ] ✅ Verify addresses before sending
- [ ] ✅ Keep software updated
- [ ] ✅ Use cold storage for large amounts
- [ ] ❌ Never share mnemonic
- [ ] ❌ Never store mnemonic digitally
- [ ] ❌ Never reuse passwords

---

## Advanced Features

### HD Wallet Derivation

Standard path (BIP44)
m/44'/0'/0'/0/0
│ │ │ │ │
│ │ │ │ └─ Address index
│ │ │ └──── Change (0=receive, 1=change)
│ │ └──────── Account
│ └──────────── Coin type (0=Bitcoin/CarbonChain)
└─────────────── Purpose (44=BIP44)
Generate address at specific path
carbonchain wallet address --path "m/44'/0'/0'/0/5"

Generate change address
carbonchain wallet address --path "m/44'/0'/0'/1/0"

### Multi-Signature Wallets

**Create 2-of-3 multisig:**

Each participant generates extended public key
carbonchain wallet xpub --index 0

Participant 1: xpub1...
Participant 2: xpub2...
Participant 3: xpub3...
Create multisig wallet
carbonchain multisig create
--m 2
--n 3
--pubkeys xpub1,xpub2,xpub3
--name "corporate-wallet"

Get multisig address
carbonchain multisig address --wallet corporate-wallet

**Sign transaction (2-of-3):**

Participant 1: Create and sign
carbonchain multisig transfer
--wallet corporate-wallet
--to 1Recipient...
--amount 100
--sign > partial1.psbt

Participant 2: Add signature
carbonchain multisig sign
--file partial1.psbt
--sign > complete.psbt

Broadcast (now has 2 signatures)
carbonchain multisig broadcast --file complete.psbt

### Stealth Addresses (Privacy)

Create stealth wallet
carbonchain stealth create --name private-wallet

Get stealth address (public)
carbonchain stealth address --wallet private-wallet

Output: sp1qABC123...
Sender uses stealth address (creates one-time address)
carbonchain wallet transfer
--to sp1qABC123...
--amount 10

Receiver scans for payments
carbonchain stealth scan --wallet private-wallet

Detects payment automatically
### Coin Control

List all UTXOs
carbonchain wallet utxos

Select specific UTXOs for transaction
carbonchain wallet transfer
--to 1Recipient...
--amount 10
--use-utxo txid1:0,txid2:1

Freeze UTXO (prevent spending)
carbonchain wallet freeze --utxo txid:index

Unfreeze
carbonchain wallet unfreeze --utxo txid:index

---

## Certificate Management

### View Certificates

List owned certificates
carbonchain wallet certificates

Output:
Your CO₂ Certificates
═══════════════════════════════════════
CERT-2025-0001
Amount: 500 tons CO₂
Compensated: 200 tons CO₂
Remaining: 300 tons CO₂
Status: PARTIALLY_COMPENSATED
### Compensate Certificates

Use certified coins for compensation
carbonchain wallet compensate
--certificate CERT-2025-0001
--amount 100

---

## Troubleshooting

### Wallet Not Found

**Issue:** "Wallet file not found"

**Solution:**
Check wallet location
ls ~/.carbonchain/wallets/

List all wallets
carbonchain wallet list

Recover from mnemonic
carbonchain wallet recover --mnemonic "your words"

### Balance Not Updating

**Issue:** Balance shows 0 after receiving payment

**Solution:**
Rescan blockchain
carbonchain wallet rescan

Force sync
carbonchain node sync

Check transaction on explorer
Wait for confirmations (6 recommended)
### Transaction Stuck

**Issue:** Transaction not confirming

**Solutions:**
Check transaction status
carbonchain wallet tx --txid abc123...

If low fee, try Replace-By-Fee (RBF)
carbonchain wallet rbf --txid abc123... --fee 0.001

Or wait (may take hours if mempool full)
### Forgot Password

**Issue:** Can't decrypt wallet file

**Solution:**
Use mnemonic to recover (bypass password)
carbonchain wallet recover --mnemonic "your 24 words"

⚠️ If you lost both mnemonic and password:
→ Funds are PERMANENTLY LOST
→ No recovery possible
### Wrong Balance

**Issue:** Balance doesn't match expected

**Solutions:**
Rescan blockchain
carbonchain wallet rescan --from-height 0

Check all addresses
carbonchain wallet addresses

Verify on block explorer
Compare with https://explorer.carbonchain.io
---

## Mobile Wallet (Future)

**Coming Soon:**
- iOS App (App Store)
- Android App (Google Play)
- Features:
  - QR code scanner
  - Push notifications
  - Biometric authentication
  - Certificate viewing

**Stay Updated:**
- https://carbonchain.io/wallet
- https://twitter.com/carbonchain

---

## Hardware Wallet Support (Future)

**Planned Integration:**
- Ledger Nano S/X
- Trezor Model T
- Benefits:
  - Private keys never leave device
  - Physical confirmation required
  - PIN/passphrase protection

---

## Resources

### Documentation
- [Official Docs](https://docs.carbonchain.io)
- [API Reference](https://api.carbonchain.io/docs)
- [Video Tutorials](https://youtube.com/carbonchain)

### Tools
- [Block Explorer](https://explorer.carbonchain.io)
- [Paper Wallet Generator](https://paperwallet.carbonchain.io)
- [Address Validator](https://validator.carbonchain.io)

### Support
- Discord: https://discord.gg/carbonchain
- Telegram: https://t.me/carbonchain
- Email: support@carbonchain.io
- Forum: https://forum.carbonchain.io

---

## Security Warning

⚠️ **NEVER:**
- Share your mnemonic phrase
- Store mnemonic digitally
- Send private keys to anyone
- Click suspicious links
- Download unofficial wallets

✅ **ALWAYS:**
- Verify addresses before sending
- Use official software only
- Keep backups secure
- Update regularly
- Test with small amounts first

---

**Last Updated:** 2025-11-27  
**Guide Version:** 1.0.0

Stay Safe! 🔐🌿