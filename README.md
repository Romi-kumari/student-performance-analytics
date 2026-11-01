# Student Performance & Academic Analytics System

A beginner-friendly Flask + MongoDB + PyMongo project with student CRUD, validation, aggregation analytics, indexes, query optimization, and Linear Regression.

## Features
- Create, list, search, filter, edit, and delete student records.
- Validation for required fields, attendance, marks, study hours, and academic year.
- MongoDB aggregation for average marks, pass rate, department statistics, and top students.
- Indexes on unique roll number, department/year, final marks, and name.
- Paginated student list and query filters.
- Linear Regression predicts final marks from previous marks, assignment marks, attendance, and study hours.
- Model evaluation: MAE, RMSE, and R² using an 80/20 train/test split.
- Includes 250 synthetic demonstration rows in CSV.

> Dataset note: `data/students_250.csv` is synthetically generated for project demonstration, not a real-world collected dataset. If your teacher requires a real dataset, replace it with an approved public dataset and adapt the field mapping.

## Requirements
- Python 3.10+
- MongoDB local server or MongoDB Atlas connection string

## Setup (Windows)
Open a terminal in this project folder:

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set `MONGO_URI` to your MongoDB connection string. Do not share your `.env` file or credentials.

Seed the 250 demo records:

```bash
python seed_data.py
```

Start the web app:

```bash
python app.py
```

Open `https://student-performance-analytics-gck1.onrender.com/`.

## Main pages
- `/` dashboard and summary KPIs
- `/students` list/search/filter/pagination
- `/students/new` create a student
- `/students/<id>/edit` edit a student
- `/analytics` department analytics and regression evaluation
- `/predict` enter features and predict a final mark
- Delete is a POST action from the list page

## Regression details
Features: previous marks, assignment marks, attendance percentage, study hours/day.
Target: final marks (0–100).
Model: `sklearn.linear_model.LinearRegression`.
Evaluation: hold-out test set (20%, fixed random seed 42), MAE, RMSE, R².

The model requires at least 20 complete rows to train; the provided CSV has 250. For a more rigorous report, compare the model against a baseline and discuss that synthetic data can make metrics unrealistically favorable.

## MongoDB operations to explain in viva
- CRUD: `insert_one`, `find`, `update_one`, `delete_one`
- Validation: server-side Python checks before writes
- Aggregation: `$group`, `$avg`, `$sum`, `$sort`
- Indexing: `create_index`
- Query optimization: filter before pagination, indexed roll number/departments, projection where appropriate, `explain("executionStats")` in MongoDB shell/Compass
- PyMongo: Python driver connecting Flask to MongoDB
- Regression: fit/predict and MAE/RMSE/R²

## Suggested viva demo
1. Show 250 rows in `data/students_250.csv`.
2. Seed the database and show collection count in MongoDB Compass.
3. Create a student with valid data; then try invalid attendance > 100.
4. Search/filter students and show pagination.
5. Show dashboard aggregation and department analytics.
6. Open `/analytics` and explain train/test split and metrics.
7. Predict final marks using `/predict`.
8. Explain indexes and compare query plans with `explain("executionStats")`.

## Important
This is a coursework starter, not a production deployment. Add authentication/authorization, CSRF protection, stronger configuration, and production server settings before deploying publicly.
