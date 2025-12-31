from pydynox import DynamoDBClient, set_correlation_id

client = DynamoDBClient()


def handler(event, context):
    # Set correlation ID from Lambda context
    set_correlation_id(context.aws_request_id)

    # All pydynox logs will include this ID
    client.put_item("users", {"pk": "USER#1", "name": "John"})
    # INFO:pydynox:put_item table=users duration_ms=8.2 wcu=1.0 correlation_id=abc-123

    return {"statusCode": 200}
