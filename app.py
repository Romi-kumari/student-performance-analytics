import os
import csv
import io
import math
from flask import make_response
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson.objectid import ObjectId
from dotenv import load_dotenv
from ml_model import train_model, predict_final_score
from flask_wtf.csrf import CSRFProtect
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)

from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()
app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("FLASK_SECRET_KEY is missing from .env")
csrf = CSRFProtect(app)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB_NAME", "student_analytics")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
db = client[DB_NAME]
students = db["students"]
users = db["users"]

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
# User model for Flask-Login
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data["_id"])
        self.name = user_data["name"]
        self.email = user_data["email"]
        self.password_hash = user_data["password_hash"]


# Load user from MongoDB during login sessions
@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = users.find_one({"_id": ObjectId(user_id)})

        if user_data:
            return User(user_data)

        return None

    except Exception:
        return None

# User Signup

# User Signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return render_template("signup.html")

        if len(name) < 2 or len(name) > 50:
            flash("Name must contain 2 to 50 characters.", "error")
            return render_template("signup.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return render_template("signup.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("signup.html")

        try:
            existing_user = users.find_one({"email": email})

            if existing_user:
                flash("An account with this email already exists.", "error")
                return render_template("signup.html")

            hashed_password = generate_password_hash(password)

            user_data = {
                "name": name,
                "email": email,
                "password_hash": hashed_password
            }

            users.insert_one(user_data)

            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("login"))

        except DuplicateKeyError:
            flash("This email is already registered. Please log in.", "error")
            return render_template("signup.html")

    return render_template("signup.html")


# User Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user_data = users.find_one({"email": email})

        if not user_data or not check_password_hash(
            user_data["password_hash"], password
        ):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        login_user(User(user_data))

        flash(f"Welcome back, {user_data['name']}!", "success")

        return redirect(url_for("dashboard"))

    return render_template("login.html")

# User Logout
@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()

    flash("You have been logged out successfully.", "success")

    return redirect(url_for("login"))

def parse_student(form):
    name = form.get("name", "").strip()
    roll_no = form.get("roll_no", "").strip().upper()
    department = form.get("department", "").strip()
    year = form.get("year", "").strip()

    # Check required fields
    if not name or not roll_no or not department or not year:
        raise ValueError("All student fields are required.")

    # Validate name and roll number
    if len(name) < 2 or len(name) > 100:
        raise ValueError("Name must contain 2 to 100 characters.")

    if len(roll_no) > 30:
        raise ValueError("Roll number cannot exceed 30 characters.")

    # Validate department
    allowed_departments = [
        "CSE", "IT", "ECE", "Mechanical", "Civil", "Business"
    ]

    if department not in allowed_departments:
        raise ValueError("Please select a valid department.")

    # Convert numeric fields
    try:
        year = int(year)
        attendance = float(form.get("attendance", ""))
        previous_marks = float(form.get("previous_marks", ""))
        assignment_marks = float(form.get("assignment_marks", ""))
        study_hours = float(form.get("study_hours", ""))
        final_marks = float(form.get("final_marks", ""))

    except (ValueError, TypeError):
        raise ValueError(
            "Enter valid numbers for year, attendance, marks and study hours."
        )

    # Reject NaN and Infinity
    numeric_values = [
        attendance,
        previous_marks,
        assignment_marks,
        study_hours,
        final_marks
    ]

    if not all(math.isfinite(value) for value in numeric_values):
        raise ValueError("Numeric values must be finite numbers.")

    # Validate academic year
    if year < 1 or year > 6:
        raise ValueError("Year must be between 1 and 6.")

    # Validate attendance
    if not 0 <= attendance <= 100:
        raise ValueError("Attendance must be between 0 and 100.")

    # Validate marks
    for label, value in [
        ("Previous marks", previous_marks),
        ("Assignment marks", assignment_marks),
        ("Final marks", final_marks)
    ]:
        if not 0 <= value <= 100:
            raise ValueError(f"{label} must be between 0 and 100.")

    # Validate study hours
    if not 0 <= study_hours <= 24:
        raise ValueError("Study hours must be between 0 and 24.")

    return {
        "name": name,
        "roll_no": roll_no,
        "department": department,
        "year": year,
        "attendance": attendance,
        "previous_marks": previous_marks,
        "assignment_marks": assignment_marks,
        "study_hours": study_hours,
        "final_marks": final_marks,
        "updated_at": datetime.utcnow()
    }

def ensure_indexes():
    students.create_index([("roll_no", ASCENDING)], unique=True, name="unique_roll_no")
    students.create_index([("department", ASCENDING), ("year", ASCENDING)], name="department_year_idx")
    students.create_index([("final_marks", DESCENDING)], name="final_marks_idx")
    students.create_index([("name", ASCENDING)], name="name_idx")
    users.create_index(
        [("email", ASCENDING)],
        unique=True,
        name="unique_user_email"
    )

@app.before_request
def check_db_and_indexes():
    # Index creation is idempotent; the database must be reachable.
    try:
        ensure_indexes()
    except PyMongoError:
        pass

@app.route("/")
@login_required
def dashboard():
    try:
        total = students.count_documents({})
        average = students.aggregate([
            {"$group": {"_id": None, "avg": {"$avg": "$final_marks"}}}
        ])
        avg_doc = next(average, None)
        average_marks = round(avg_doc["avg"], 2) if avg_doc else 0
        pass_count = students.count_documents({"final_marks": {"$gte": 40}})
        pass_rate = round(pass_count * 100 / total, 1) if total else 0
        department_stats = list(students.aggregate([
            {"$group": {"_id": "$department", "students": {"$sum": 1}, "average_marks": {"$avg": "$final_marks"}}},
            {"$sort": {"average_marks": -1}}
        ]))
        top_students = list(students.find({}, {"name": 1, "roll_no": 1, "department": 1, "final_marks": 1}).sort("final_marks", DESCENDING).limit(5))
        recent_students = list(students.find().sort("updated_at", DESCENDING).limit(8))
        return render_template("dashboard.html", total=total, average_marks=average_marks,
                               pass_rate=pass_rate, department_stats=department_stats,
                               top_students=top_students, recent_students=recent_students)
    except PyMongoError as exc:
        return render_template("error.html", message="Cannot connect to MongoDB. Check MONGO_URI in .env and ensure MongoDB is running.", detail=str(exc)), 503

@app.route("/students")
@login_required
def student_list():
    query = request.args.get("q", "").strip()
    department = request.args.get("department", "").strip()
    try:
        filt = {}
        if query:
            # Literal substring search, escaped to avoid treating input as regex syntax.
            import re
            safe_query = re.escape(query)
            filt["$or"] = [{"name": {"$regex": safe_query, "$options": "i"}},
                           {"roll_no": {"$regex": safe_query, "$options": "i"}}]
        if department:
            filt["department"] = department
        page = max(1, int(request.args.get("page", 1)))
        page_size = 20
        total = students.count_documents(filt)
        docs = list(students.find(filt).sort("roll_no", ASCENDING).skip((page - 1) * page_size).limit(page_size))
        departments = students.distinct("department")
        return render_template("students.html", docs=docs, query=query, department=department,
                               departments=departments, page=page, pages=max(1, (total + page_size - 1)//page_size), total=total)
    except (PyMongoError, ValueError) as exc:
        flash(f"Could not load students: {exc}", "error")
        return redirect(url_for("dashboard"))

# Export Student Records to CSV
@app.route("/students/export")
@login_required
def export_students():
    try:
        records = list(
            students.find({}, {"_id": 0}).sort("roll_no", ASCENDING)
        )

        if not records:
            flash("No student records available to export.", "error")
            return redirect(url_for("student_list"))

        output = io.StringIO()

        fieldnames = [
            "name",
            "roll_no",
            "department",
            "year",
            "attendance",
            "previous_marks",
            "assignment_marks",
            "study_hours",
            "final_marks"
        ]

        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )

        writer.writeheader()
        writer.writerows(records)

        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = (
            "attachment; filename=student_records.csv"
        )

        return response

    except Exception:
        flash("Unable to export student records.", "error")
        return redirect(url_for("student_list"))
@app.route("/students/new", methods=["GET", "POST"])
@login_required
def create_student():

    if request.method == "POST":
        try:
            data = parse_student(request.form)
            students.insert_one(data)

            flash("Student created successfully.", "success")
            return redirect(url_for("student_list"))

        except ValueError as exc:
            flash(str(exc), "error")

        except DuplicateKeyError:
            flash(
                "This roll number already exists. Please use a different roll number.",
                "error"
            )

        except PyMongoError:
            flash(
                "A database error occurred. Please try again.",
                "error"
            )

    # Display the form for GET requests or after validation errors
    return render_template(
        "student_form.html",
        title="Add Student",
        student=None
    )



@app.route("/students/<student_id>/edit", methods=["GET", "POST"])
@login_required
def edit_student(student_id):

    try:
        student = students.find_one({"_id": ObjectId(student_id)})
    except Exception:
        student = None

    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("student_list"))

    if request.method == "POST":
        try:
            data = parse_student(request.form)

            students.update_one(
                {"_id": student["_id"]},
                {"$set": data}
            )

            flash("Student updated successfully.", "success")
            return redirect(url_for("student_list"))

        except ValueError as exc:
            flash(str(exc), "error")

        except DuplicateKeyError:
            flash(
                "This roll number already belongs to another student. Please use a different roll number.",
                "error"
            )

        except PyMongoError:
            flash(
                "A database error occurred while updating the student.",
                "error"
            )

    return render_template(
        "student_form.html",
        student=student,
        title="Edit Student"
    )

@app.route("/students/<student_id>/delete", methods=["POST"])
@login_required
def delete_student(student_id):
    try:
        result = students.delete_one({"_id": ObjectId(student_id)})
        flash("Student deleted." if result.deleted_count else "Student not found.", "success")
    except Exception:
        flash("Invalid student ID.", "error")
    return redirect(url_for("student_list"))

@app.route("/analytics")
@login_required
def analytics():
    try:
        stats = list(students.aggregate([
            {"$group": {"_id": "$department", "count": {"$sum": 1}, "avg_previous": {"$avg": "$previous_marks"},
                        "avg_final": {"$avg": "$final_marks"}, "avg_attendance": {"$avg": "$attendance"}}},
            {"$sort": {"_id": 1}}
        ]))
        model_info = train_model(students)
        return render_template("analytics.html", stats=stats, model_info=model_info)
    except (PyMongoError, ValueError) as exc:
        return render_template("error.html", message="Analytics could not be calculated.", detail=str(exc)), 500


@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    prediction = None
    error = None

    if request.method == "POST":
        try:
            # Get input values
            previous_marks = float(request.form.get("previous_marks", ""))
            assignment_marks = float(request.form.get("assignment_marks", ""))
            attendance = float(request.form.get("attendance", ""))
            study_hours = float(request.form.get("study_hours", ""))

            # Reject NaN and Infinity
            values = [
                previous_marks,
                assignment_marks,
                attendance,
                study_hours
            ]

            if not all(math.isfinite(value) for value in values):
                raise ValueError("Please enter finite numeric values.")

            # Validate marks
            if not 0 <= previous_marks <= 100:
                raise ValueError("Previous marks must be between 0 and 100.")

            if not 0 <= assignment_marks <= 100:
                raise ValueError("Assignment marks must be between 0 and 100.")

            if not 0 <= attendance <= 100:
                raise ValueError("Attendance must be between 0 and 100.")

            # Validate study hours
            if not 0 <= study_hours <= 24:
                raise ValueError("Study hours must be between 0 and 24.")

            # Generate prediction
            prediction = predict_final_score(
                students,
                previous_marks,
                assignment_marks,
                attendance,
                study_hours
            )

        except (ValueError, KeyError) as exc:
            error = str(exc)

        except PyMongoError:
            error = "A database error occurred. Please try again."

    return render_template(
        "predict.html",
        prediction=prediction,
        error=error
    )

if __name__ == "__main__":
    print("\nREGISTERED ROUTES:")
    for rule in app.url_map.iter_rules():
        print(rule.endpoint, "->", rule)

    app.run(
    debug=False,
    use_reloader=False,
    port=int(os.getenv("PORT", "5001"))
)
