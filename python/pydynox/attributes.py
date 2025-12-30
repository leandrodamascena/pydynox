"""Attribute types for Model definitions."""

from datetime import datetime, timedelta, timezone
from typing import Any, Generic, Optional, TypeVar

from pydynox._compression import (
    CompressionAlgorithm,
    compress_string,
    decompress_string,
)

T = TypeVar("T")

__all__ = [
    "Attribute",
    "StringAttribute",
    "NumberAttribute",
    "BooleanAttribute",
    "BinaryAttribute",
    "ListAttribute",
    "MapAttribute",
    "TTLAttribute",
    "ExpiresIn",
    "CompressedAttribute",
    "CompressionAlgorithm",
]


class Attribute(Generic[T]):
    """Base attribute class for Model fields.

    Attributes define the schema of a DynamoDB item. They can be marked
    as hash_key or range_key to define the table's primary key.

    Example:
        >>> class User(Model):
        ...     pk = StringAttribute(hash_key=True)
        ...     sk = StringAttribute(range_key=True)
        ...     name = StringAttribute()
        ...     age = NumberAttribute()
    """

    attr_type: str = "S"  # Default to string

    def __init__(
        self,
        hash_key: bool = False,
        range_key: bool = False,
        default: Optional[T] = None,
        null: bool = True,
    ):
        """Create an attribute.

        Args:
            hash_key: True if this is the partition key.
            range_key: True if this is the sort key.
            default: Default value when not provided.
            null: Whether None is allowed.
        """
        self.hash_key = hash_key
        self.range_key = range_key
        self.default = default
        self.null = null
        self.attr_name: Optional[str] = None

    def serialize(self, value: T) -> Any:
        """Convert Python value to DynamoDB format."""
        return value

    def deserialize(self, value: Any) -> T:
        """Convert DynamoDB value to Python format."""
        return value


class StringAttribute(Attribute[str]):
    """String attribute (DynamoDB type S)."""

    attr_type = "S"


class NumberAttribute(Attribute[float]):
    """Number attribute (DynamoDB type N).

    Stores both int and float values.
    """

    attr_type = "N"


class BooleanAttribute(Attribute[bool]):
    """Boolean attribute (DynamoDB type BOOL)."""

    attr_type = "BOOL"


class BinaryAttribute(Attribute[bytes]):
    """Binary attribute (DynamoDB type B)."""

    attr_type = "B"


class ListAttribute(Attribute[list]):
    """List attribute (DynamoDB type L)."""

    attr_type = "L"


class MapAttribute(Attribute[dict]):
    """Map attribute (DynamoDB type M)."""

    attr_type = "M"


class ExpiresIn:
    """Helper class to create TTL datetime values.

    Makes it easy to set expiration times without manual datetime math.

    Example:
        >>> from pydynox.attributes import ExpiresIn
        >>> expires = ExpiresIn.hours(1)  # 1 hour from now
        >>> expires = ExpiresIn.days(7)   # 7 days from now
    """

    @staticmethod
    def seconds(n: int) -> datetime:
        """Return datetime n seconds from now.

        Args:
            n: Number of seconds.

        Returns:
            datetime in UTC.
        """
        return datetime.now(timezone.utc) + timedelta(seconds=n)

    @staticmethod
    def minutes(n: int) -> datetime:
        """Return datetime n minutes from now.

        Args:
            n: Number of minutes.

        Returns:
            datetime in UTC.
        """
        return datetime.now(timezone.utc) + timedelta(minutes=n)

    @staticmethod
    def hours(n: int) -> datetime:
        """Return datetime n hours from now.

        Args:
            n: Number of hours.

        Returns:
            datetime in UTC.
        """
        return datetime.now(timezone.utc) + timedelta(hours=n)

    @staticmethod
    def days(n: int) -> datetime:
        """Return datetime n days from now.

        Args:
            n: Number of days.

        Returns:
            datetime in UTC.
        """
        return datetime.now(timezone.utc) + timedelta(days=n)

    @staticmethod
    def weeks(n: int) -> datetime:
        """Return datetime n weeks from now.

        Args:
            n: Number of weeks.

        Returns:
            datetime in UTC.
        """
        return datetime.now(timezone.utc) + timedelta(weeks=n)


class TTLAttribute(Attribute[datetime]):
    """TTL attribute for DynamoDB Time-To-Live.

    Stores datetime as epoch timestamp (number). DynamoDB uses this
    to auto-delete expired items.

    Example:
        >>> from pydynox import Model
        >>> from pydynox.attributes import StringAttribute, TTLAttribute, ExpiresIn
        >>>
        >>> class Session(Model):
        ...     class Meta:
        ...         table = "sessions"
        ...     pk = StringAttribute(hash_key=True)
        ...     expires_at = TTLAttribute()
        >>>
        >>> session = Session(pk="SESSION#123", expires_at=ExpiresIn.hours(1))
        >>> session.save()
    """

    attr_type = "N"

    def serialize(self, value: datetime) -> int:
        """Convert datetime to epoch timestamp.

        Args:
            value: datetime object.

        Returns:
            Unix timestamp as integer.
        """
        return int(value.timestamp())

    def deserialize(self, value: Any) -> datetime:
        """Convert epoch timestamp to datetime.

        Args:
            value: Unix timestamp (int or float).

        Returns:
            datetime object in UTC.
        """
        return datetime.fromtimestamp(float(value), tz=timezone.utc)


class CompressedAttribute(Attribute[str]):
    """Attribute that auto-compresses large text values.

    Stores data as base64-encoded compressed binary in DynamoDB.
    Compression happens automatically on save, decompression on load.
    All heavy work (compression + base64) is done in Rust for speed.

    Args:
        algorithm: Compression algorithm to use. Options:
            - CompressionAlgorithm.Zstd (default): Best compression ratio
            - CompressionAlgorithm.Lz4: Fastest
            - CompressionAlgorithm.Gzip: Good balance
        level: Compression level. Higher = smaller but slower.
            - zstd: 1-22 (default 3)
            - gzip: 0-9 (default 6)
            - lz4: ignored
        min_size: Minimum size in bytes to compress (default 100).
            Smaller values are stored as-is.
        threshold: Compression ratio threshold (default 0.9).
            Only compress if result is smaller by this ratio.
        hash_key: True if this is the partition key.
        range_key: True if this is the sort key.
        default: Default value when not provided.
        null: Whether None is allowed.

    Example:
        >>> from pydynox import Model
        >>> from pydynox.attributes import StringAttribute, CompressedAttribute
        >>>
        >>> class Document(Model):
        ...     class Meta:
        ...         table = "documents"
        ...     pk = StringAttribute(hash_key=True)
        ...     body = CompressedAttribute()  # Uses zstd by default
        ...     logs = CompressedAttribute(algorithm=CompressionAlgorithm.Lz4)
    """

    attr_type = "S"  # Stored as base64 string

    def __init__(
        self,
        algorithm: Optional["CompressionAlgorithm"] = None,
        level: Optional[int] = None,
        min_size: int = 100,
        threshold: float = 0.9,
        hash_key: bool = False,
        range_key: bool = False,
        default: Optional[str] = None,
        null: bool = True,
    ):
        """Create a compressed attribute.

        Args:
            algorithm: Compression algorithm (default: zstd).
            level: Compression level.
            min_size: Minimum bytes to trigger compression.
            threshold: Only compress if ratio is below this.
            hash_key: True if this is the partition key.
            range_key: True if this is the sort key.
            default: Default value when not provided.
            null: Whether None is allowed.
        """
        super().__init__(
            hash_key=hash_key,
            range_key=range_key,
            default=default,
            null=null,
        )
        self.algorithm = algorithm
        self.level = level
        self.min_size = min_size
        self.threshold = threshold

    def serialize(self, value: str) -> str:
        """Compress and encode value for DynamoDB.

        Args:
            value: String to compress.

        Returns:
            Base64-encoded compressed data with prefix, or original if
            compression not worthwhile.
        """
        if value is None:
            return None

        # All done in Rust: compression + base64 + prefix
        return compress_string(
            value,
            self.algorithm,
            self.level,
            self.min_size,
            self.threshold,
        )

    def deserialize(self, value: Any) -> str:
        """Decompress value from DynamoDB.

        Args:
            value: Stored value (may be compressed or plain).

        Returns:
            Original string.
        """
        if value is None:
            return None

        if not isinstance(value, str):
            return str(value)

        # All done in Rust: detect prefix + base64 decode + decompress
        return decompress_string(value)
