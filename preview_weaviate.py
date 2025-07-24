import weaviate
from pprint import pprint

# Initialize the client
client = weaviate.Client(
    url="http://127.0.0.1:8079",
)

# Get schema information
schema = client.schema.get()
print("\n=== Schema ===")
pprint(schema)

# Get all objects from the log class
print("\n=== Logs ===")
result = (
    client.query
    .get("Log")
    .with_additional(["id", "vector", "creationTimeUnix"])
    .with_limit(10)
    .do()
)
pprint(result)

# Get class statistics
print("\n=== Statistics ===")
stats = client.query.aggregate("Log").with_meta_count().do()
pprint(stats) 