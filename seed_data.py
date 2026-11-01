"""Insert 250 clearly synthetic demonstration student records into MongoDB.
Run only on a development database. Existing roll numbers are skipped."""
import csv
import os
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import BulkWriteError

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = client[os.getenv("MONGO_DB_NAME", "student_analytics")]
collection = db["students"]
collection.create_index([("roll_no", ASCENDING)], unique=True, name="unique_roll_no")
collection.create_index([("department", ASCENDING), ("year", ASCENDING)], name="department_year_idx")
collection.create_index([("final_marks", DESCENDING)], name="final_marks_idx")
collection.create_index([("name", ASCENDING)], name="name_idx")

rows = []
with open("data/students_250.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        rows.append({
            "name": row["name"], "roll_no": row["roll_no"], "department": row["department"],
            "year": int(row["year"]), "attendance": float(row["attendance"]),
            "previous_marks": float(row["previous_marks"]), "assignment_marks": float(row["assignment_marks"]),
            "study_hours": float(row["study_hours"]), "final_marks": float(row["final_marks"]),
            "updated_at": datetime.utcnow(), "data_source": "synthetic_demo"
        })
inserted = 0
for row in rows:
    result = collection.update_one({"roll_no": row["roll_no"]}, {"$setOnInsert": row}, upsert=True)
    inserted += result.upserted_id is not None
print(f"CSV rows: {len(rows)}; newly inserted: {inserted}; collection total: {collection.count_documents({})}")
