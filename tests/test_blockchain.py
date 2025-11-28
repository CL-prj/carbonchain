"""
CarbonChain - Wallet Tests
============================
Unit tests for HD Wallet functionality.
"""

import pytest
from carbon_chain.wallet.hd_wallet import HDWallet
from carbon_chain.errors import InvalidMnemonicError


class TestHDWallet:
    """Test HD Wallet class"""
    
    def test_wallet_creation(self, test_config):
        """Test wallet creation"""
        wallet = HDWallet.create_new(strength=128, config=test_config)
        
        assert wallet is not None
        mnemonic = wallet.get_mnemonic()
        assert len(mnemonic.split()) == 12
    
    def test_wallet_recovery(self, test_config):
        """Test wallet recovery from mnemonic"""
        # Create wallet
        wallet1 = HDWallet.create_new(strength=128, config=test_config)
        mnemonic = wallet1.get_mnemonic()
        address1 = wallet1.get_address(0)
        
        # Recover wallet
        wallet2 = HDWallet.from_mnemonic(mnemonic, config=test_config)
        address2 = wallet2.get_address(0)
        
        assert address1 == address2
    
    def test_address_derivation(self, wallet):
        """Test deterministic address derivation"""
        addresses = [wallet.get_address(i) for i in range(5)]
        
        # All addresses unique
        assert len(set(addresses)) == 5
        
        # Deterministic: same index = same address
        assert wallet.get_address(0) == wallet.get_address(0)
    
    def test_invalid_mnemonic(self, test_config):
        """Test invalid mnemonic rejection"""
        with pytest.raises(InvalidMnemonicError):
            HDWallet.from_mnemonic("invalid mnemonic phrase", config=test_config)
    
    def test_wallet_encryption(self, wallet):
        """Test wallet export/import with encryption"""
        password = "test_password_123"
        
        # Export encrypted
        encrypted = wallet.export_encrypted(password)
        
        assert "encrypted_mnemonic" in encrypted
        assert "salt" in encrypted
        assert "nonce" in encrypted
        
        # Import encrypted
        wallet2 = HDWallet.import_encrypted(encrypted, password)
        
        # Same addresses
        assert wallet.get_address(0) == wallet2.get_address(0)
