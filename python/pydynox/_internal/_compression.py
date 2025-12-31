"""Internal compression functions. Do not use directly."""

from __future__ import annotations

from pydynox import pydynox_core

CompressionAlgorithm = pydynox_core.CompressionAlgorithm
compress = pydynox_core.compress
decompress = pydynox_core.decompress
compress_string = pydynox_core.compress_string
decompress_string = pydynox_core.decompress_string
should_compress = pydynox_core.should_compress
