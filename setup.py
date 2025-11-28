"""
CarbonChain - Setup Configuration
===================================
Package installation configuration.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith('#') and not line.startswith('-r')
        ]

setup(
    name="carbonchain",
    version="1.0.0",
    author="CarbonChain Team",
    author_email="info@carbonchain.example.com",
    description="Blockchain for CO2 certification and compensation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Cimmizio/carbonchain",
    project_urls={
        "Bug Tracker": "https://github.com/Cimmizio/carbonchain/issues",
        "Documentation": "https://carbonchain.readthedocs.io",
        "Source Code": "https://github.com/Cimmizio/carbonchain",
    },
    packages=find_packages(exclude=["tests", "tests.*", "docs", "scripts"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Typing :: Typed",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.11.0",
            "mypy>=1.7.0",
            "ruff>=0.1.6",
        ],
        "docs": [
            "sphinx>=7.2.0",
            "sphinx-rtd-theme>=2.0.0",
            "sphinx-autodoc-typehints>=1.25.0",
        ],
        "pq": [
            # "liboqs-python>=0.8.0",  # Uncomment when available
        ],
    },
    entry_points={
        "console_scripts": [
            "carbonchain=carbon_chain.cli.main:app",
        ],
    },
    include_package_data=True,
    package_data={
        "carbon_chain": ["py.typed"],
    },
    zip_safe=False,
    keywords=[
        "blockchain",
        "cryptocurrency",
        "co2",
        "carbon",
        "certification",
        "compensation",
        "climate",
        "sustainability",
    ],
)
