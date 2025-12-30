## Title

refactor: replace class Meta with ModelConfig

## Body

Closes #43

### What changed

The old `class Meta` pattern was confusing. It mixed client config (region, endpoint) with table config, and there was no way to reuse a configured client across models.

Now we have `ModelConfig` - a dataclass with type hints and IDE autocomplete.

**Before:**
```python
class User(Model):
    class Meta:
        table = "users"
        region = "us-east-1"  # Where does this go?
    pk = StringAttribute(hash_key=True)
```

**After:**
```python
client = DynamoDBClient(region="us-east-1", profile="prod")
set_default_client(client)

class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
```

### Changes

- Added `config.py` with `ModelConfig` dataclass
- Added `set_default_client()`, `get_default_client()`, `clear_default_client()`
- Updated `Model` to use `ModelConfig` instead of `class Meta`
- Updated all tests (unit + integration)
- Updated all examples in `docs/examples/`
- Updated documentation
- Added new guide `docs/guides/00-client.md` for DynamoDBClient

### How client resolution works

1. Check `model_config.client` first
2. Fall back to default client (set via `set_default_client()`)
3. Error if neither is set

### Tests

All 261 tests pass (159 unit + 102 integration).
