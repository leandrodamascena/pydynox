"""Tests for compression module."""

import pytest
from pydynox._internal._compression import (
    CompressionAlgorithm,
    compress,
    compress_string,
    decompress,
    decompress_string,
    should_compress,
)
from pydynox.attributes import CompressedAttribute

# --- Low-level compression functions ---


@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(CompressionAlgorithm.Zstd, id="zstd"),
        pytest.param(CompressionAlgorithm.Lz4, id="lz4"),
        pytest.param(CompressionAlgorithm.Gzip, id="gzip"),
    ],
)
def test_compress_decompress_roundtrip(algorithm):
    """Compress and decompress returns original data."""
    original = b"hello world " * 100
    compressed = compress(original, algorithm)
    result = decompress(compressed, algorithm)

    assert result == original


@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(CompressionAlgorithm.Zstd, id="zstd"),
        pytest.param(CompressionAlgorithm.Lz4, id="lz4"),
        pytest.param(CompressionAlgorithm.Gzip, id="gzip"),
    ],
)
def test_compression_reduces_size(algorithm):
    """Compression makes data smaller."""
    original = b"hello world " * 1000
    compressed = compress(original, algorithm)

    assert len(compressed) < len(original)


def test_compress_default_algorithm():
    """Default algorithm is zstd."""
    original = b"hello world " * 100
    compressed = compress(original)
    result = decompress(compressed)  # Also uses default

    assert result == original


def test_should_compress_large_data():
    """should_compress returns True for large compressible data."""
    data = b"hello world " * 1000

    assert should_compress(data) is True


def test_should_compress_small_data():
    """should_compress returns False for small data."""
    data = b"hi"

    assert should_compress(data) is False


def test_should_compress_threshold():
    """should_compress respects threshold parameter."""
    data = b"hello world " * 100

    # Loose threshold - should compress
    result_loose = should_compress(data, threshold=0.99)

    assert result_loose is True


# --- compress_string / decompress_string (Rust fast path) ---


@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(CompressionAlgorithm.Zstd, id="zstd"),
        pytest.param(CompressionAlgorithm.Lz4, id="lz4"),
        pytest.param(CompressionAlgorithm.Gzip, id="gzip"),
    ],
)
def test_compress_string_roundtrip(algorithm):
    """compress_string and decompress_string roundtrip works."""
    original = "hello world " * 100
    compressed = compress_string(original, algorithm, min_size=10)
    result = decompress_string(compressed)

    assert result == original


def test_compress_string_small_not_compressed():
    """Small strings are not compressed."""
    original = "hi"
    result = compress_string(original, min_size=100)

    assert result == original  # Unchanged


def test_compress_string_adds_prefix():
    """Compressed strings have algorithm prefix."""
    original = "hello world " * 100
    result = compress_string(original, CompressionAlgorithm.Zstd, min_size=10)

    assert result.startswith("ZSTD:")


def test_decompress_string_plain():
    """decompress_string returns plain strings unchanged."""
    plain = "hello world"
    result = decompress_string(plain)

    assert result == plain


# --- CompressedAttribute ---


def test_compressed_attribute_type():
    """CompressedAttribute has string type for base64 storage."""
    attr = CompressedAttribute()

    assert attr.attr_type == "S"


def test_compressed_attribute_default_algorithm():
    """Default algorithm is None (Rust uses zstd)."""
    attr = CompressedAttribute()

    # None means Rust will use zstd as default
    assert attr.algorithm is None


@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(CompressionAlgorithm.Zstd, id="zstd"),
        pytest.param(CompressionAlgorithm.Lz4, id="lz4"),
        pytest.param(CompressionAlgorithm.Gzip, id="gzip"),
    ],
)
def test_compressed_attribute_roundtrip(algorithm):
    """Serialize and deserialize returns original value."""
    attr = CompressedAttribute(algorithm=algorithm, min_size=10)
    original = "hello world " * 100

    serialized = attr.serialize(original)
    result = attr.deserialize(serialized)

    assert result == original


def test_compressed_attribute_small_value_not_compressed():
    """Small values are not compressed."""
    attr = CompressedAttribute(min_size=100)
    original = "hi"

    serialized = attr.serialize(original)

    # Should be stored as-is, no prefix
    assert serialized == original
    assert not serialized.startswith("ZSTD:")


def test_compressed_attribute_large_value_compressed():
    """Large values are compressed with prefix."""
    attr = CompressedAttribute(min_size=10)
    original = "hello world " * 100

    serialized = attr.serialize(original)

    # Should have compression prefix
    assert serialized.startswith("ZSTD:")


@pytest.mark.parametrize(
    "algorithm,prefix",
    [
        pytest.param(CompressionAlgorithm.Zstd, "ZSTD:", id="zstd"),
        pytest.param(CompressionAlgorithm.Lz4, "LZ4:", id="lz4"),
        pytest.param(CompressionAlgorithm.Gzip, "GZIP:", id="gzip"),
    ],
)
def test_compressed_attribute_prefix(algorithm, prefix):
    """Each algorithm has correct prefix."""
    attr = CompressedAttribute(algorithm=algorithm, min_size=10)
    original = "hello world " * 100

    serialized = attr.serialize(original)

    assert serialized.startswith(prefix)


def test_compressed_attribute_none_value():
    """None values are handled correctly."""
    attr = CompressedAttribute()

    assert attr.serialize(None) is None
    assert attr.deserialize(None) is None


def test_compressed_attribute_uncompressed_deserialize():
    """Deserialize handles uncompressed values."""
    attr = CompressedAttribute()
    plain = "hello world"

    result = attr.deserialize(plain)

    assert result == plain


def test_compressed_attribute_custom_level():
    """Custom compression level works."""
    attr = CompressedAttribute(level=10, min_size=10)
    original = "hello world " * 100

    serialized = attr.serialize(original)
    result = attr.deserialize(serialized)

    assert result == original


def test_compressed_attribute_threshold():
    """Threshold controls when compression happens."""
    # Very strict threshold - won't compress
    attr_strict = CompressedAttribute(threshold=0.01, min_size=10)
    original = "hello world " * 10

    serialized = attr_strict.serialize(original)

    # Should not be compressed due to strict threshold
    assert not serialized.startswith("ZSTD:")


def test_compressed_attribute_key_flags():
    """CompressedAttribute supports hash_key and range_key."""
    hash_attr = CompressedAttribute(hash_key=True)
    range_attr = CompressedAttribute(range_key=True)

    assert hash_attr.hash_key is True
    assert hash_attr.range_key is False
    assert range_attr.hash_key is False
    assert range_attr.range_key is True
