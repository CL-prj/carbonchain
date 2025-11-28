"""
CarbonChain - Merkle Tree Implementation
==========================================
Merkle tree for transaction verification.
"""

import hashlib
from typing import List, Optional
from dataclasses import dataclass

from carbon_chain.logging_setup import get_logger

logger = get_logger("utils.merkle")


# ============================================================================
# MERKLE TREE
# ============================================================================

@dataclass
class MerkleNode:
    """
    Node in Merkle tree.
    
    Attributes:
        hash: Node hash
        left: Left child
        right: Right child
    """
    hash: bytes
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    
    def is_leaf(self) -> bool:
        """Check if leaf node"""
        return self.left is None and self.right is None


class MerkleTree:
    """
    Merkle tree for efficient transaction verification.
    
    Examples:
        >>> txids = [b"tx1", b"tx2", b"tx3", b"tx4"]
        >>> tree = MerkleTree(txids)
        >>> root = tree.get_root()
        >>> proof = tree.get_proof(b"tx2")
        >>> is_valid = tree.verify_proof(b"tx2", proof, root)
    """
    
    def __init__(self, leaves: List[bytes]):
        """
        Initialize Merkle tree.
        
        Args:
            leaves: List of leaf hashes (e.g., transaction IDs)
        """
        if not leaves:
            raise ValueError("Cannot create Merkle tree with no leaves")
        
        self.leaves = leaves
        self.root = self._build_tree(leaves)
    
    def _build_tree(self, hashes: List[bytes]) -> MerkleNode:
        """
        Build Merkle tree from leaf hashes.
        
        Args:
            hashes: List of hashes
        
        Returns:
            MerkleNode: Root node
        """
        # Create leaf nodes
        nodes = [MerkleNode(hash=h) for h in hashes]
        
        # Build tree bottom-up
        while len(nodes) > 1:
            # If odd number of nodes, duplicate last one
            if len(nodes) % 2 == 1:
                nodes.append(nodes[-1])
            
            # Create parent level
            parent_nodes = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1]
                
                # Compute parent hash
                parent_hash = self._hash_pair(left.hash, right.hash)
                parent = MerkleNode(hash=parent_hash, left=left, right=right)
                parent_nodes.append(parent)
            
            nodes = parent_nodes
        
        return nodes[0]
    
    def _hash_pair(self, left: bytes, right: bytes) -> bytes:
        """
        Hash pair of nodes (double SHA-256).
        
        Args:
            left: Left hash
            right: Right hash
        
        Returns:
            bytes: Combined hash
        """
        combined = left + right
        return hashlib.sha256(hashlib.sha256(combined).digest()).digest()
    
    def get_root(self) -> bytes:
        """
        Get Merkle root hash.
        
        Returns:
            bytes: Root hash
        """
        return self.root.hash
    
    def get_proof(self, leaf: bytes) -> List[tuple[bytes, str]]:
        """
        Get Merkle proof for leaf.
        
        Args:
            leaf: Leaf hash to prove
        
        Returns:
            List[tuple]: List of (hash, position) where position is 'left' or 'right'
        
        Raises:
            ValueError: If leaf not found
        """
        if leaf not in self.leaves:
            raise ValueError(f"Leaf not found in tree")
        
        proof = []
        leaf_index = self.leaves.index(leaf)
        
        # Reconstruct path to root
        current_level = [MerkleNode(hash=h) for h in self.leaves]
        current_index = leaf_index
        
        while len(current_level) > 1:
            # Duplicate last node if odd number
            if len(current_level) % 2 == 1:
                current_level.append(current_level[-1])
            
            # Find sibling
            if current_index % 2 == 0:
                # Current is left, sibling is right
                sibling = current_level[current_index + 1]
                proof.append((sibling.hash, 'right'))
            else:
                # Current is right, sibling is left
                sibling = current_level[current_index - 1]
                proof.append((sibling.hash, 'left'))
            
            # Move to parent level
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1]
                parent_hash = self._hash_pair(left.hash, right.hash)
                next_level.append(MerkleNode(hash=parent_hash))
            
            current_level = next_level
            current_index = current_index // 2
        
        return proof
    
    def verify_proof(
        self,
        leaf: bytes,
        proof: List[tuple[bytes, str]],
        root: bytes
    ) -> bool:
        """
        Verify Merkle proof.
        
        Args:
            leaf: Leaf hash
            proof: Merkle proof
            root: Expected root hash
        
        Returns:
            bool: True if proof valid
        """
        current_hash = leaf
        
        for sibling_hash, position in proof:
            if position == 'left':
                current_hash = self._hash_pair(sibling_hash, current_hash)
            else:  # right
                current_hash = self._hash_pair(current_hash, sibling_hash)
        
        return current_hash == root


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def compute_merkle_root(hashes: List[bytes]) -> bytes:
    """
    Compute Merkle root from list of hashes.
    
    Args:
        hashes: List of hashes
    
    Returns:
        bytes: Merkle root
    
    Examples:
        >>> txids = [b"tx1", b"tx2", b"tx3"]
        >>> root = compute_merkle_root(txids)
    """
    if not hashes:
        return b'\x00' * 32
    
    if len(hashes) == 1:
        return hashes[0]
    
    tree = MerkleTree(hashes)
    return tree.get_root()


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "MerkleNode",
    "MerkleTree",
    "compute_merkle_root",
]
