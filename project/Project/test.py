from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient('mongodb://127.0.0.1:27017/')
db = client["mydatabase"]
collection = db["users"]

collection.insert_one({"name": "Alice", "age": 30})

users = [
    {"name": "Bob", "age": 25},
    {"name": "Charlie", "age": 35}
]
collection.insert_many(users)

for user in collection.find():
    print(user)
user = collection.find_one({"name": "Alice"})
print(user)
collection.update_one({"name": "Alice"}, {"$set": {"age": 40}})

collection.delete_one({"name": "Bob"})

client.close()
