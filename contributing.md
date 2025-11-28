# Contributing to CarbonChain

Thank you for your interest in contributing to CarbonChain! 🌍

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

**Bug Report Template:**
- **Description**: Clear description of the bug
- **Steps to Reproduce**: Detailed steps
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: OS, Python version, CarbonChain version
- **Logs**: Relevant error logs

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues.

**Enhancement Template:**
- **Use Case**: Why is this enhancement needed?
- **Proposed Solution**: How would it work?
- **Alternatives**: Other solutions considered
- **Additional Context**: Screenshots, mockups, etc.

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/my-new-feature`
3. **Make your changes**
4. **Add tests** for new functionality
5. **Update documentation** if needed
6. **Run tests**: `pytest tests/`
7. **Format code**: `black carbon_chain/`
8. **Commit**: `git commit -m 'Add some feature'`
9. **Push**: `git push origin feature/my-new-feature`
10. **Open a Pull Request**

## Development Setup

Clone your fork
git clone https://github.com/YOUR_USERNAME/carbonchain.git
cd carbonchain

Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

Install in development mode
pip install -e ".[dev]"

Run tests
pytest tests/ -v --cov=carbon_chain

## Coding Standards

### Python Style Guide

- Follow **PEP 8**
- Use **Black** for formatting (line length: 100)
- Use **type hints** everywhere
- Write **Google-style docstrings**

**Example:**

def calculate_subsidy(height: int) -> int:
"""
Calcola subsidy per blocco dato height.

text
Args:
    height: Block height

Returns:
    int: Subsidy in Satoshi

Examples:
    >>> calculate_subsidy(0)
    50000000
"""
halvings = height // HALVING_INTERVAL
if halvings >= 64:
    return 0
return INITIAL_SUBSIDY_SATOSHI >> halvings
### Testing

- Write tests for **all new features**
- Maintain **80%+ code coverage**
- Use **pytest** fixtures for setup
- Test **edge cases** and **error conditions**

**Test Example:**

def test_blockchain_add_block(blockchain):
"""Test adding valid block to blockchain."""
# Setup
initial_height = blockchain.get_height()

text
# Mine block
block = blockchain.mine_block(
    miner_address="1TestAddress",
    transactions=[],
    timeout_seconds=60
)

# Add block
blockchain.add_block(block)

# Assert
assert blockchain.get_height() == initial_height + 1
assert blockchain.get_latest_block() == block
### Documentation

- Update README.md for user-facing changes
- Add docstrings to all public functions/classes
- Update API documentation
- Include code examples

### Commit Messages

Follow **Conventional Commits**:

type(scope): subject

body

footer

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**
feat(wallet): add multi-signature support

Implement BIP-11 compatible multi-signature wallets with 2-of-3 and 3-of-5 configurations.

Closes #123

## Project Structure

carbon_chain/
├── domain/ # Core blockchain logic
├── wallet/ # Wallet management
├── services/ # High-level services
├── storage/ # Database layer
├── api/ # REST API
├── cli/ # Command-line interface
├── config.py # Configuration
├── constants.py # Protocol constants
├── errors.py # Custom exceptions
└── logging_setup.py # Logging setup

## Security

### Reporting Security Issues

**DO NOT** open public issues for security vulnerabilities.

Email security issues to: **security@carbonchain.eco**

We will respond within 48 hours.

### Security Guidelines

- Never commit private keys or secrets
- Use `.env` for sensitive configuration
- Validate all user inputs
- Follow cryptographic best practices
- Keep dependencies updated

## Testing Guidelines

### Unit Tests

Run all tests
pytest tests/

Run specific test file
pytest tests/test_blockchain.py

Run with coverage
pytest --cov=carbon_chain --cov-report=html

### Integration Tests

Run integration tests
pytest tests/integration/ -v

### Performance Tests

Run benchmark tests
pytest tests/benchmarks/ --benchmark-only

## Documentation

### Building Documentation

Install docs dependencies
pip install -e ".[docs]"

Build HTML docs
cd docs/
make html

View docs
open _build/html/index.html

## Release Process

1. Update version in `pyproject.toml` and `carbon_chain/__init__.py`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag -a v1.0.0 -m "Release v1.0.0"`
4. Push tag: `git push origin v1.0.0`
5. Create GitHub release
6. Build and upload to PyPI

## Community

- **GitHub Discussions**: Ask questions, share ideas
- **Discord**: Real-time chat with developers
- **Twitter**: Follow @CarbonChainCO2 for updates

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to a more transparent and sustainable future! 🌱
📁 FILE 36: CHANGELOG.md
Percorso: CHANGELOG.md

text
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- P2P networking layer
- Node discovery via DNS seeds
- Mempool transaction propagation
- Multi-signature wallet support

## [1.0.0] - 2025-01-15

### Added
- **Core Blockchain**
  - Proof of Work consensus (Scrypt algorithm)
  - Block validation and chain management
  - UTXO set with efficient indexing
  - Genesis block creation
  - Difficulty adjustment (Bitcoin-like)
  - Supply halving mechanism

- **Transaction System**
  - COINBASE transactions (mining rewards)
  - TRANSFER transactions (coin transfers)
  - ASSIGN_CERT transactions (certificate assignment)
  - ASSIGN_COMPENSATION transactions (compensation tracking)
  - BURN transactions (coin destruction)
  - Transaction validation and signing
  - Mempool with priority ordering

- **Certificate Management**
  - Certificate assignment to coins
  - Unique certificate hash enforcement
  - Capacity tracking (total vs issued vs compensated)
  - Metadata support (ISO 14064, GHG Protocol, etc.)
  - Certificate state tracking
  - Query API for certificates

- **Compensation Tracking**
  - Project registration
  - Immutable compensation records
  - Project type categorization
  - Statistics and analytics
  - Certificate-to-project linking

- **Wallet**
  - HD Wallet (BIP39/BIP44 compatible)
  - 12/24 word mnemonic generation
  - Deterministic address derivation
  - Transaction signing
  - Encrypted wallet export/import (AES-256-GCM)
  - Balance queries

- **Storage**
  - SQLite database persistence
  - Block and transaction indexing
  - UTXO set storage
  - Certificate and project tracking
  - Thread-safe operations

- **API**
  - REST API (FastAPI)
  - Blockchain queries
  - Wallet operations
  - Certificate management
  - Compensation operations
  - Mining control
  - OpenAPI documentation

- **CLI**
  - Node management commands
  - Wallet operations
  - Certificate assignment
  - Mining control
  - Blockchain queries
  - Rich terminal UI

- **Services**
  - WalletService (high-level wallet ops)
  - CertificateService (certificate management)
  - CompensationService (compensation ops)
  - MiningService (mining orchestration)
  - ProjectService (project queries)

- **Security**
  - ECDSA signatures (secp256k1)
  - SHA-256 and BLAKE2b hashing
  - AES-256-GCM encryption
  - PBKDF2 key derivation
  - Scrypt for PoW
  - Address validation
  - Signature verification

- **Developer Tools**
  - Python SDK
  - Complete type hints
  - Comprehensive docstrings
  - Example scripts
  - Testing utilities

### Documentation
- Comprehensive README.md
- API documentation
- Code examples
- Architecture overview
- Contributing guidelines
- License (MIT)

### Infrastructure
- Python 3.10+ support
- Virtual environment setup
- Dependencies management (pyproject.toml)
- Testing framework (pytest)
- Code formatting (black, ruff)
- Type checking (mypy)
- Logging system
- Configuration management

## [0.2.0] - 2024-12-01

### Added
- Basic blockchain structure
- Transaction model
- Wallet prototype
- Certificate concept

### Changed
- Refactored validation logic
- Improved error handling

## [0.1.0] - 2024-11-01

### Added
- Initial project setup
- Core domain models
- Basic cryptography functions
- Project documentation

---

**Legend:**
- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for now removed features
- `Fixed` for any bug fixes
- `Security` in case of vulnerabilities