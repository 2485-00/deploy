from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

db = client["testdb"]
collection = db["students"]

print("Connected to MongoDB")

# CREATE (Insert)
# collection.insert_one({"name": "Ali", "age": 20})
# collection.insert_many([
#     {"name": "Sara", "age": 22},
#     {"name": "John", "age": 25}
# ])

# READ (Find)
for doc in collection.find():
    print(doc)

# UPDATE
collection.update_one(
    {"name": "Ali"},
    {"$set": {"age": 21}}
)



# DELETE
collection.delete_one({"name": "John"})

# READ (Find)
for doc in collection.find():
    print(doc)

# # Filter Query
# for doc in collection.find({"age": {"$gt": 20}}):
#     print(doc)

# # Projection (select fields)
# for doc in collection.find({}, {"name": 1, "_id": 0}):
#     print(doc)

# # Sorting
# for doc in collection.find().sort("age", -1):
#     print(doc)

# # Limit
# for doc in collection.find().limit(2):
#     print(doc)
