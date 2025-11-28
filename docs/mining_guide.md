# CarbonChain - Mining Guide

Complete guide to mining CarbonChain blocks and earning rewards.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Mining Basics](#mining-basics)
3. [Setting Up a Miner](#setting-up-a-miner)
4. [Solo Mining](#solo-mining)
5. [Pool Mining](#pool-mining)
6. [Mining Hardware](#mining-hardware)
7. [Profitability](#profitability)
8. [Troubleshooting](#troubleshooting)

---

## Introduction

CarbonChain uses **Proof of Work (PoW)** consensus with **Scrypt** or **Argon2id** algorithms. Mining secures the network and validates transactions while rewarding miners with newly minted CCO₂ coins.

### Why Mine CarbonChain?

✅ **Eco-Friendly Mission** - Support CO₂ certificate verification  
✅ **Fair Launch** - No pre-mine or ICO  
✅ **Predictable Rewards** - Fixed block reward schedule  
✅ **ASIC-Resistant** - Optimized for consumer hardware  

---

## Mining Basics

### Block Reward Schedule

Block 0 - 210,000: 50 CCO₂ per block
Block 210,001 - 420,000: 25 CCO₂ per block
Block 420,001 - 630,000: 12.5 CCO₂ per block
...
Maximum Supply: 21,000,000 CCO₂


**Halving:** Every 210,000 blocks (~4 years)

### Block Time

- **Target:** 10 minutes per block
- **Difficulty Adjustment:** Every 2016 blocks (~2 weeks)
- **Algorithm:** Scrypt (default) or Argon2id

### Mining Difficulty

difficulty = previous_difficulty * (target_time / actual_time)
difficulty = max(difficulty * 0.25, min(difficulty * 4.0, difficulty))


**Constraints:**
- Max increase: 4x per adjustment
- Max decrease: 4x per adjustment

---

## Setting Up a Miner

### System Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 4 GB
- Storage: 10 GB SSD
- Network: 5 Mbps

**Recommended:**
- CPU: 8+ cores (AMD Ryzen 5/Intel i7)
- RAM: 8 GB+
- Storage: 50 GB NVMe SSD
- Network: 20+ Mbps
- GPU: Optional (Scrypt-compatible)

### Software Installation

#### 1. Install CarbonChain

Clone repository
git clone https://github.com/carbonchain/carbonchain.git
cd carbonchain

Install dependencies
pip install -r requirements.txt

Install CarbonChain
pip install -e .


#### 2. Verify Installation

carbonchain --version

Output: CarbonChain v1.0.0

#### 3. Initialize Node

Initialize blockchain
carbonchain node init --network mainnet

Check node info
carbonchain node info


---

## Solo Mining

### Create Mining Wallet

Create new wallet
carbonchain wallet create --strength 256

Output:
⚠️ BACKUP YOUR MNEMONIC PHRASE!
word1 word2 word3 ... word24
First address: 1YourMiningAddress...
IMPORTANT: Save mnemonic in a safe place!

### Start Mining

Start solo mining
carbonchain mine start --address 0 --threads 4

Output:
⛏️ Mining started...
Using 4 threads
Difficulty: 1048576
Target: 000000abc123...
⛏️ Mining block #12346...
✅ Block found! Hash: 000000def456...
💰 Reward: 50.00000000 CCO₂

### Mining Parameters

Custom thread count
carbonchain mine start --threads 8

Specific address index
carbonchain mine start --address 1

Limited blocks (stop after N blocks)
carbonchain mine start --blocks 10

Custom algorithm
carbonchain mine start --algorithm argon2id


### Monitor Mining

Check mining status
carbonchain mining stats

Output:
Mining Status
═══════════════════════════════════
Status: Active
Hashrate: 1.5 MH/s
Blocks Found: 3
Last Block: 12348 (2 minutes ago)
Difficulty: 1048576
Estimated: Next block in ~8 minutes

### Stop Mining

Stop mining
carbonchain mine stop

Or press Ctrl+C

---

## Pool Mining

### Why Join a Pool?

✅ **Consistent Rewards** - Regular small payments  
✅ **Lower Variance** - Predictable income  
✅ **No Full Node Required** - Pool manages blockchain  

❌ **Pool Fees** - Typically 1-3%  
❌ **Centralization** - Less network decentralization  

### Connect to Pool

Install mining software (cgminer/sgminer)
sudo apt-get install cgminer

Configure pool
cat > pool.conf << EOF
{
"pools": [
{
"url": "stratum+tcp://pool.carbonchain.io:3333",
"user": "YOUR_WALLET_ADDRESS",
"pass": "x"
}
],
"algorithm": "scrypt",
"intensity": "13",
"worksize": "256",
"thread-concurrency": "8192"
}
EOF

Start mining
cgminer --config pool.conf


### Popular Pools

| Pool | Fee | Location | URL |
|------|-----|----------|-----|
| CarbonPool | 1% | Global | pool.carbonchain.io |
| EcoMine | 2% | EU | ecomine.io |
| GreenHash | 1.5% | US | greenhash.io |

*(Note: Example pools - actual pools TBD)*

---

## Mining Hardware

### CPU Mining

**Best CPUs for Mining:**
- AMD Ryzen 9 5950X (16 cores)
- AMD Threadripper 3990X (64 cores)
- Intel Core i9-12900K (16 cores)

**Expected Hashrate:**
- 4 cores: ~500 KH/s
- 8 cores: ~1 MH/s
- 16 cores: ~2 MH/s

**Configuration:**
Optimize CPU mining
carbonchain mine start
--threads $(nproc)
--affinity 0-$(nproc)
--priority high


### GPU Mining

**Supported GPUs (Scrypt):**
- AMD RX 6800/6900 series
- AMD RX 5700 series
- NVIDIA RTX 3070/3080/3090 (limited)

**GPU Mining Setup:**
Install GPU miner
git clone https://github.com/sgminer-dev/sgminer.git
cd sgminer
./autogen.sh
./configure
make

Start GPU mining
./sgminer
--algorithm scrypt
--url http://localhost:9333
--userpass user:pass
--intensity 13


**Expected Hashrate:**
- AMD RX 6900: ~15 MH/s
- AMD RX 5700: ~10 MH/s
- NVIDIA RTX 3090: ~8 MH/s

### ASIC Resistance

CarbonChain is designed to be **ASIC-resistant** using memory-hard algorithms:

**Scrypt Parameters:**
- N: 1024 (memory cost)
- r: 1 (block size)
- p: 1 (parallelization)

**Argon2id Parameters:**
- Memory: 64 MB
- Iterations: 3
- Parallelism: 4

---

## Profitability

### Calculate Profitability

Mining Calculator
hashrate = 2_000_000 # 2 MH/s
network_hashrate = 100_000_000 # 100 MH/s
block_reward = 50 # CCO2
blocks_per_day = 144 # (24 * 60 / 10)

Your share of network
share = hashrate / network_hashrate

Expected daily earnings
daily_blocks = blocks_per_day * share
daily_earnings = daily_blocks * block_reward

print(f"Daily Earnings: {daily_earnings:.4f} CCO2")

Output: Daily Earnings: 1.4400 CCO2

### Profitability Factors

1. **Hashrate** - Your mining speed
2. **Network Difficulty** - Total network mining power
3. **Electricity Cost** - Power consumption × price
4. **Hardware Cost** - Initial investment
5. **CCO₂ Price** - Market value

### Break-Even Analysis

ROI = (Hardware Cost + Monthly Power Cost) / Monthly Earnings

Example:

Hardware: $1,500

Power: 150W × $0.12/kWh × 720h = $12.96/month

Earnings: 43.2 CCO2/month × $10 = $432/month

ROI: ($1,500 + $12.96) / $432 = 3.5 months


**Online Calculators:**
- https://calculator.carbonchain.io *(example URL)*

---

## Advanced Mining

### Optimize Performance

#### 1. CPU Affinity

Pin mining threads to specific cores
carbonchain mine start
--threads 8
--affinity 0,1,2,3,4,5,6,7


#### 2. Memory Optimization

Increase memory allocation
export MALLOC_ARENA_MAX=2
export MALLOC_MMAP_THRESHOLD_=131072


#### 3. Process Priority

Run with high priority (Linux)
sudo nice -n -20 carbonchain mine start

Or use renice
sudo renice -n -20 -p $(pgrep carbonchain)


### Mining Scripts

**Auto-restart script:**
#!/bin/bash

mine-restart.sh
while true; do
carbonchain mine start --address 0

# If mining stops, wait and restart
sleep 10
echo "Restarting miner..."
done


**Monitoring script:**
#!/bin/bash

monitor-mining.sh
while true; do
stats=$(carbonchain mining stats)
echo "$(date): $stats"

# Alert if hashrate drops
hashrate=$(echo "$stats" | grep Hashrate | awk '{print $2}')
if (( $(echo "$hashrate < 1.0" | bc -l) )); then
    echo "WARNING: Low hashrate detected!"
    # Send notification (email, SMS, etc.)
fi

sleep 60
done


### Failover Configuration

Primary node
carbonchain mine start --address 0 --node localhost:9333

If primary fails, use backup
carbonchain mine start --address 0 --node backup.carbonchain.io:9333


---

## Mining Best Practices

### Security

✅ **Use dedicated wallet** - Separate mining from storage  
✅ **Enable firewall** - Only open necessary ports  
✅ **Regular backups** - Backup wallet every week  
✅ **Monitor logs** - Check for suspicious activity  

### Efficiency

✅ **Stable connection** - Reliable internet (UPS recommended)  
✅ **Cool environment** - Keep hardware under 80°C  
✅ **Clean power** - Use quality PSU with surge protection  
✅ **Update software** - Latest miner version for best performance  

### Environmental

✅ **Use renewable energy** - Solar, wind, hydro  
✅ **Optimize cooling** - Natural airflow, efficient fans  
✅ **Recycle heat** - Use mining heat for home heating  

---

## Troubleshooting

### Mining Not Starting

**Issue:** Miner fails to start

**Solutions:**
Check node is running
carbonchain node info

Check wallet exists
carbonchain wallet list

Check logs
tail -f ~/.carbonchain/logs/mining.log

Verify network connection
ping pool.carbonchain.io


### Low Hashrate

**Issue:** Lower than expected hashrate

**Solutions:**
Check CPU usage
top -p $(pgrep carbonchain)

Increase thread count
carbonchain mine start --threads 16

Check for thermal throttling
sensors # Linux

Check CPU temperature < 80°C
Close other applications
Disable browser, games, etc.

### No Blocks Found

**Issue:** Mining for hours without finding blocks

**Explanation:** This is normal with high network difficulty

**Solutions:**
Check estimated time
carbonchain mining stats

Consider joining a pool
Or wait longer (solo mining has high variance)
Verify you're on correct chain
carbonchain node info

Check block hash matches explorer

### High Reject Rate

**Issue:** Many submitted blocks rejected

**Solutions:**
Check system time (must be accurate)
sudo ntpdate -s time.nist.gov

Update to latest version
pip install --upgrade carbonchain

Check network latency
ping pool.carbonchain.io

Reduce thread count if CPU overloaded
carbonchain mine start --threads 4


### Connection Issues

**Issue:** Can't connect to pool/node

**Solutions:**
Check network connectivity
ping pool.carbonchain.io

Check firewall rules
sudo ufw allow 9333/tcp

Try alternative pool
carbonchain mine start --node backup.carbonchain.io:9333

Check pool status
curl http://pool.carbonchain.io/stats


---

## Mining Pool Setup (Advanced)

### Run Your Own Pool

**Requirements:**
- Dedicated server (8GB RAM, 4 cores)
- Static IP address
- Domain name
- CarbonChain full node

**Installation:**
Install pool software (example)
git clone https://github.com/carbonchain/pool.git
cd pool

Configure
cp config.example.json config.json
nano config.json

Start pool
npm install
npm start


**Pool Configuration:**
{
"pool": {
"address": "your_pool_address",
"fee": 1.0,
"min_payout": 1.0
},
"stratum": {
"port": 3333,
"difficulty": 16
},
"daemon": {
"host": "localhost",
"port": 9333
}
}


---

## Resources

### Documentation
- [CarbonChain Docs](https://docs.carbonchain.io)
- [Mining FAQ](https://carbonchain.io/mining-faq)
- [Discord Community](https://discord.gg/carbonchain)

### Tools
- [Mining Calculator](https://calculator.carbonchain.io)
- [Block Explorer](https://explorer.carbonchain.io)
- [Pool List](https://pools.carbonchain.io)

### Software
- [Official Miner](https://github.com/carbonchain/carbonchain)
- [cgminer](https://github.com/ckolivas/cgminer)
- [sgminer](https://github.com/sgminer-dev/sgminer)

---

## Support

**Need Help?**
- Discord: https://discord.gg/carbonchain
- Telegram: https://t.me/carbonchain
- Email: mining@carbonchain.io
- Forum: https://forum.carbonchain.io

---

**Last Updated:** 2025-11-27  
**Guide Version:** 1.0.0

Happy Mining! ⛏️🌿