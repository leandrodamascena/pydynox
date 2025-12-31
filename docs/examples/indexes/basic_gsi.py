"""Basic GSI example - query users by email."""

from pydynox import DynamoDBClient, GlobalSecondaryIndex, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute

# Setup client
client = DynamoDBClient(endpoint_url="http://localhost:8000")
set_default_client(client)


class User(Model):
    """User model with email GSI."""

    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    email = StringAttribute()
    name = StringAttribute()
    age = NumberAttribute()

    # Define GSI to query by email
    email_index = GlobalSecondaryIndex(
        index_name="email-index",
        hash_key="email",
    )


# Create table with GSI
if not client.table_exists("users"):
    client.create_table(
        "users",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        global_secondary_indexes=[
            {
                "index_name": "email-index",
                "hash_key": ("email", "S"),
                "projection": "ALL",
            }
        ],
    )

# Create some users
User(pk="USER#1", sk="PROFILE", email="john@example.com", name="John", age=30).save()
User(pk="USER#2", sk="PROFILE", email="jane@example.com", name="Jane", age=25).save()

# Query by email using GSI
print("Query by email:")
for user in User.email_index.query(email="john@example.com"):
    print(f"  Found: {user.name} (pk={user.pk})")
