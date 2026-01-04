"""Primitive attribute types (String, Number, Boolean, Binary, List, Map)."""

from __future__ import annotations

from typing import Any

from pydynox.attributes.base import Attribute


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


class ListAttribute(Attribute[list[Any]]):
    """List attribute (DynamoDB type L)."""

    attr_type = "L"


class MapAttribute(Attribute[dict[str, Any]]):
    """Map attribute (DynamoDB type M)."""

    attr_type = "M"
