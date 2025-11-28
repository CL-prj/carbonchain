#!/bin/bash
# CarbonChain - Local Network Deployment
# =======================================
# Deploy multi-node local testnet for development

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NODES=3
BASE_PORT=19333
BASE_API_PORT=18000
BASE_EXPLORER_PORT=18080
NETWORK="regtest"
DATA_DIR="./localnet"

echo -e "${GREEN}🌿 CarbonChain Local Network Deployment${NC}"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not installed${NC}"
    exit 1
fi

# Check if CarbonChain is installed
if ! python3 -c "import carbon_chain" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  CarbonChain not installed. Installing...${NC}"
    pip install -e .
fi

# Clean previous data
if [ -d "$DATA_DIR" ]; then
    echo -e "${YELLOW}⚠️  Previous data found. Cleaning...${NC}"
    rm -rf "$DATA_DIR"
fi

# Create directories
mkdir -p "$DATA_DIR"
for i in $(seq 1 $NODES); do
    mkdir -p "$DATA_DIR/node$i/data"
    mkdir -p "$DATA_DIR/node$i/logs"
done

echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# Generate wallets
echo -e "${GREEN}🔑 Generating wallets...${NC}"
for i in $(seq 1 $NODES); do
    python3 -c "
from carbon_chain.wallet.hd_wallet import HDWallet
import json

wallet = HDWallet.create(strength=128)
address = wallet.get_address(0)

data = {
    'mnemonic': wallet.mnemonic,
    'address': address
}

with open('$DATA_DIR/node$i/wallet.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f'Node $i: {address}')
"
done

echo -e "${GREEN}✅ Wallets generated${NC}"
echo ""

# Create genesis block
echo -e "${GREEN}⛓️  Creating genesis block...${NC}"
NODE1_ADDR=$(python3 -c "import json; print(json.load(open('$DATA_DIR/node1/wallet.json'))['address'])")

python3 scripts/bootstrap_genesis.py \
    --network $NETWORK \
    --data-dir "$DATA_DIR/node1/data" \
    --reward-address "$NODE1_ADDR" \
    --genesis-message "CarbonChain Localnet Genesis"

echo -e "${GREEN}✅ Genesis block created${NC}"
echo ""

# Start nodes
echo -e "${GREEN}🚀 Starting nodes...${NC}"

for i in $(seq 1 $NODES); do
    PORT=$((BASE_PORT + i - 1))
    API_PORT=$((BASE_API_PORT + i - 1))
    EXPLORER_PORT=$((BASE_EXPLORER_PORT + i - 1))
    
    # Get node address
    NODE_ADDR=$(python3 -c "import json; print(json.load(open('$DATA_DIR/node$i/wallet.json'))['address'])")
    
    # Build seed nodes list (connect to node 1)
    if [ $i -eq 1 ]; then
        SEED_NODES=""
    else
        SEED_NODES="--seed-nodes 127.0.0.1:$BASE_PORT"
    fi
    
    echo -e "${YELLOW}Starting Node $i...${NC}"
    echo "  Port: $PORT"
    echo "  API: $API_PORT"
    echo "  Explorer: $EXPLORER_PORT"
    echo "  Address: $NODE_ADDR"
    
    # Start node in background
    nohup python3 -m carbon_chain.cli node start \
        --network $NETWORK \
        --data-dir "$DATA_DIR/node$i/data" \
        --p2p-port $PORT \
        --api-port $API_PORT \
        --explorer-port $EXPLORER_PORT \
        $SEED_NODES \
        > "$DATA_DIR/node$i/logs/node.log" 2>&1 &
    
    echo $! > "$DATA_DIR/node$i/node.pid"
    echo ""
    
    # Wait a bit between nodes
    sleep 2
done

echo -e "${GREEN}✅ All nodes started${NC}"
echo ""

# Wait for nodes to start
echo -e "${YELLOW}⏳ Waiting for nodes to initialize...${NC}"
sleep 5

# Check node status
echo -e "${GREEN}📊 Node Status:${NC}"
for i in $(seq 1 $NODES); do
    API_PORT=$((BASE_API_PORT + i - 1))
    if curl -s http://localhost:$API_PORT/health > /dev/null 2>&1; then
        echo -e "  Node $i: ${GREEN}✅ Running${NC}"
    else
        echo -e "  Node $i: ${RED}❌ Failed${NC}"
    fi
done

echo ""
echo "========================================"
echo -e "${GREEN}🎉 Local network deployed successfully!${NC}"
echo "========================================"
echo ""
echo "Access points:"
for i in $(seq 1 $NODES); do
    API_PORT=$((BASE_API_PORT + i - 1))
    EXPLORER_PORT=$((BASE_EXPLORER_PORT + i - 1))
    echo "  Node $i API:      http://localhost:$API_PORT"
    echo "  Node $i Explorer: http://localhost:$EXPLORER_PORT"
done
echo ""
echo "Management commands:"
echo "  Stop all nodes:  ./scripts/stop_localnet.sh"
echo "  View logs:       tail -f $DATA_DIR/node1/logs/node.log"
echo ""

# Create stop script
cat > scripts/stop_localnet.sh << 'EOF'
#!/bin/bash
# Stop CarbonChain local network

DATA_DIR="./localnet"

echo "🛑 Stopping CarbonChain local network..."

for pid_file in $DATA_DIR/node*/node.pid; do
    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            echo "  Stopped node (PID: $PID)"
        fi
        rm "$pid_file"
    fi
done

echo "✅ All nodes stopped"
EOF

chmod +x scripts/stop_localnet.sh

echo -e "${YELLOW}💡 Tip: Mine some blocks with:${NC}"
echo "   carbonchain mine start --address 0 --blocks 10"
echo ""
