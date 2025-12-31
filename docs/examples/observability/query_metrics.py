from pydynox import DynamoDBClient

client = DynamoDBClient()

# Query returns a result object with .metrics
result = client.query(
    "users",
    key_condition_expression="#pk = :pk",
    expression_attribute_names={"#pk": "pk"},
    expression_attribute_values={":pk": "ORG#123"},
)

# Iterate over results
for item in result:
    print(item["name"])

# Access metrics after iteration
print(result.metrics.duration_ms)  # 45.2
print(result.metrics.consumed_rcu)  # 2.5
print(result.metrics.items_count)  # 10
