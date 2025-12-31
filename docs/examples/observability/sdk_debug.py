import logging

from pydynox import DynamoDBClient, set_logger

# Create a logger
logger = logging.getLogger("pydynox")
logger.setLevel(logging.DEBUG)

# Enable SDK debug logs
set_logger(logger, sdk_debug=True)

# Now you'll see detailed AWS SDK logs
client = DynamoDBClient()
client.get_item("users", {"pk": "USER#1"})
