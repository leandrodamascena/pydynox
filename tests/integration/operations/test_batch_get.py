"""Integration tests for batch_get operation."""


def test_batch_get_returns_items(dynamo):
    """Test batch get with a few items."""
    # First, put some items
    items = [
        {"pk": "BGET#1", "sk": "ITEM#1", "name": "Alice"},
        {"pk": "BGET#1", "sk": "ITEM#2", "name": "Bob"},
        {"pk": "BGET#1", "sk": "ITEM#3", "name": "Charlie"},
    ]
    for item in items:
        dynamo.put_item("test_table", item)

    # Batch get them
    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    results = dynamo.batch_get("test_table", keys)

    # Verify all items were returned
    assert len(results) == 3
    names = {r["name"] for r in results}
    assert names == {"Alice", "Bob", "Charlie"}


def test_batch_get_missing_items_not_returned(dynamo):
    """Test batch get with some missing items."""
    # Put only one item
    dynamo.put_item("test_table", {"pk": "MISS#1", "sk": "EXISTS", "name": "Found"})

    # Try to get two items (one exists, one doesn't)
    keys = [
        {"pk": "MISS#1", "sk": "EXISTS"},
        {"pk": "MISS#1", "sk": "NOTEXISTS"},
    ]
    results = dynamo.batch_get("test_table", keys)

    # Only the existing item should be returned
    assert len(results) == 1
    assert results[0]["name"] == "Found"


def test_batch_get_empty_keys_returns_empty(dynamo):
    """Test batch get with empty keys list."""
    results = dynamo.batch_get("test_table", [])
    assert results == []


def test_batch_get_more_than_100_items(dynamo):
    """Test batch get with more than 100 items.

    DynamoDB limits batch gets to 100 items per request.
    The client should split the request into multiple batches.
    Requirements: 7.6
    """
    # Create 120 items (more than the 100-item limit)
    items = [
        {"pk": "LARGE#1", "sk": f"ITEM#{i:03d}", "index": i, "data": f"value_{i}"}
        for i in range(120)
    ]
    dynamo.batch_write("test_table", put_items=items)

    # Batch get all 120 items
    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    results = dynamo.batch_get("test_table", keys)

    # Verify all 120 items were returned
    assert len(results) == 120
    indices = {r["index"] for r in results}
    assert indices == set(range(120))


def test_batch_get_exactly_100_items(dynamo):
    """Test batch get with exactly 100 items (the limit)."""
    items = [{"pk": "EXACT#1", "sk": f"ITEM#{i:02d}", "value": i} for i in range(100)]
    dynamo.batch_write("test_table", put_items=items)

    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    results = dynamo.batch_get("test_table", keys)

    assert len(results) == 100
    values = {r["value"] for r in results}
    assert values == set(range(100))


def test_batch_get_150_items(dynamo):
    """Test batch get with 150 items (requires 2 batches)."""
    items = [{"pk": "ONEFIFTY#1", "sk": f"ITEM#{i:03d}", "num": i} for i in range(150)]
    dynamo.batch_write("test_table", put_items=items)

    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    results = dynamo.batch_get("test_table", keys)

    assert len(results) == 150
    nums = {r["num"] for r in results}
    assert nums == set(range(150))


def test_batch_get_with_various_types(dynamo):
    """Test batch get with items containing various data types."""
    items = [
        {
            "pk": "TYPES#1",
            "sk": "ITEM#1",
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "list": [1, 2, 3],
            "map": {"nested": "value"},
        },
        {
            "pk": "TYPES#1",
            "sk": "ITEM#2",
            "string": "world",
            "number": -100,
            "float": 0.001,
            "bool": False,
            "list": ["a", "b"],
            "map": {"key": 123},
        },
    ]
    dynamo.batch_write("test_table", put_items=items)

    keys = [{"pk": item["pk"], "sk": item["sk"]} for item in items]
    results = dynamo.batch_get("test_table", keys)

    assert len(results) == 2

    # Build a lookup by sk for easier verification
    by_sk = {r["sk"]: r for r in results}

    for item in items:
        result = by_sk[item["sk"]]
        for field, value in item.items():
            assert result[field] == value
