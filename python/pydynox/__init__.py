"""pydynox - A fast DynamoDB client for Python with a Rust core.

Example:
    >>> from pydynox import DynamoClient
    >>> client = DynamoClient(region="us-east-1")
    >>> client.ping()
    True
"""

# Import from Rust core
from pydynox import pydynox_core

# Import Python wrappers
from .query import QueryResult
from .client import DynamoClient

__version__ = "0.1.0"

__all__ = [
    "DynamoClient",
    "QueryResult",
    "__version__",
]
