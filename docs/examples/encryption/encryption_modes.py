"""Encryption modes example."""

from pydynox import Model
from pydynox.attributes import EncryptedAttribute, EncryptionMode, StringAttribute


# Write-only service: can encrypt, cannot decrypt
class IngestService(Model):
    class Meta:
        table = "users"

    pk = StringAttribute(hash_key=True)
    ssn = EncryptedAttribute(
        key_id="alias/my-app-key",
        mode=EncryptionMode.WriteOnly,
    )


# Read-only service: can decrypt, cannot encrypt
class ReportService(Model):
    class Meta:
        table = "users"

    pk = StringAttribute(hash_key=True)
    ssn = EncryptedAttribute(
        key_id="alias/my-app-key",
        mode=EncryptionMode.ReadOnly,
    )


# Full access (default): can encrypt and decrypt
class AdminService(Model):
    class Meta:
        table = "users"

    pk = StringAttribute(hash_key=True)
    ssn = EncryptedAttribute(key_id="alias/my-app-key")
