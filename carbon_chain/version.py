"""
CarbonChain - Version Management
==================================
Gestione versioning semantico e build info.

Security Level: MEDIUM
Last Updated: 2025-11-26
Version: 1.0.0
"""

from typing import NamedTuple
from datetime import datetime


# ============================================================================
# VERSION INFO
# ============================================================================

class VersionInfo(NamedTuple):
    """Version information structure"""
    major: int
    minor: int
    patch: int
    prerelease: str = ""
    build: str = ""


# Current version (Semantic Versioning)
VERSION = VersionInfo(
    major=1,
    minor=0,
    patch=0,
    prerelease="",  # alpha, beta, rc1, etc.
    build=""  # Build metadata
)


def get_version_string() -> str:
    """
    Get version as string.
    
    Returns:
        str: Version (e.g., "1.0.0", "1.0.0-beta", "1.0.0+build123")
    
    Example:
        >>> get_version_string()
        '1.0.0'
    """
    version_str = f"{VERSION.major}.{VERSION.minor}.{VERSION.patch}"
    
    if VERSION.prerelease:
        version_str += f"-{VERSION.prerelease}"
    
    if VERSION.build:
        version_str += f"+{VERSION.build}"
    
    return version_str


def get_version_tuple() -> tuple:
    """Get version as tuple"""
    return (VERSION.major, VERSION.minor, VERSION.patch)


def is_compatible(other_version: str) -> bool:
    """
    Check protocol compatibility with another version.
    
    Args:
        other_version: Version string to check
    
    Returns:
        bool: True if compatible
    
    Rules:
        - Same major version = compatible
        - Different major version = incompatible
    """
    try:
        other_major = int(other_version.split('.')[0])
        return other_major == VERSION.major
    except:
        return False


# ============================================================================
# BUILD INFO
# ============================================================================

BUILD_DATE = "2025-11-26"
BUILD_TIME = "22:00:00 UTC"
BUILD_TIMESTAMP = int(datetime(2025, 11, 26, 22, 0, 0).timestamp())

# Git info (populated during build)
GIT_COMMIT_HASH = ""  # Short hash (7 chars)
GIT_BRANCH = ""
GIT_TAG = ""

# Build environment
BUILD_PLATFORM = "multi"  # darwin, linux, windows
BUILD_ARCH = "multi"  # x86_64, arm64
PYTHON_VERSION_MIN = "3.12"


def get_build_info() -> dict:
    """
    Get complete build information.
    
    Returns:
        dict: Build metadata
    """
    return {
        "version": get_version_string(),
        "version_tuple": get_version_tuple(),
        "build_date": BUILD_DATE,
        "build_time": BUILD_TIME,
        "build_timestamp": BUILD_TIMESTAMP,
        "git_commit": GIT_COMMIT_HASH or "unknown",
        "git_branch": GIT_BRANCH or "unknown",
        "git_tag": GIT_TAG or "unknown",
        "platform": BUILD_PLATFORM,
        "arch": BUILD_ARCH,
        "python_min": PYTHON_VERSION_MIN,
    }


# ============================================================================
# USER AGENT
# ============================================================================

def get_user_agent() -> str:
    """
    Get User-Agent string for P2P handshake.
    
    Format: /CarbonChain:1.0.0/
    
    Returns:
        str: User agent
    """
    return f"/CarbonChain:{get_version_string()}/"


# ============================================================================
# EXPORT
# ============================================================================

__version__ = get_version_string()
__version_info__ = VERSION

__all__ = [
    "__version__",
    "__version_info__",
    "VERSION",
    "get_version_string",
    "get_version_tuple",
    "is_compatible",
    "get_build_info",
    "get_user_agent",
]
