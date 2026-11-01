
import numpy as np

from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

FEATURES = [
    "previous_marks",
    "assignment_marks",
    "attendance",
    "study_hours"
]

TARGET = "final_marks"


def _records(collection):
    return list(collection.find(
        {
            key: {"$exists": True}
            for key in FEATURES + [TARGET]
        },
        {
            key: 1
            for key in FEATURES + [TARGET]
        }
    ))


def train_model(collection):
    records = _records(collection)

    if len(records) < 20:
        return {
            "trained": False,
            "count": len(records),
            "message": "Add at least 20 complete student records before training the model."
        }

    X = np.array([
        [float(r[k]) for k in FEATURES]
        for r in records
    ])

    y = np.array([
        float(r[TARGET])
        for r in records
    ])

    if len(np.unique(y)) < 2:
        return {
            "trained": False,
            "count": len(records),
            "message": "The dataset needs variation in final marks."
        }

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    model = LinearRegression()
    model.fit(X_train, y_train)

    predicted = np.clip(
        model.predict(X_test),
        0,
        100
    )

    # Evaluation metrics
    mae = float(mean_absolute_error(y_test, predicted))
    rmse = float(np.sqrt(mean_squared_error(y_test, predicted)))
    r2 = float(r2_score(y_test, predicted))

    # Residual errors
    residuals = y_test - predicted

    # Actual vs predicted chart data
    actual_vs_predicted = [
        {
            "x": round(float(actual), 2),
            "y": round(float(pred), 2)
        }
        for actual, pred in zip(y_test, predicted)
    ]

    # Residual chart data
    residual_plot = [
        {
            "x": round(float(pred), 2),
            "y": round(float(error), 2)
        }
        for pred, error in zip(predicted, residuals)
    ]

    # Regression coefficients
    coefficients = {
        key: round(float(value), 3)
        for key, value in zip(FEATURES, model.coef_)
    }

    return {
        "trained": True,
        "count": len(records),

        "train_count": len(X_train),
        "test_count": len(X_test),

        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "r2": round(r2, 3),

        "coefficients": coefficients,

        "intercept": round(float(model.intercept_), 3),

        # Data for regression visualizations
        "actual_vs_predicted": actual_vs_predicted,
        "residual_plot": residual_plot,

        "feature_labels": [
            "Previous Marks",
            "Assignment Marks",
            "Attendance",
            "Study Hours"
        ],

        "coefficient_values": [
            coefficients[key]
            for key in FEATURES
        ]
    }


def predict_final_score(
    collection,
    previous_marks,
    assignment_marks,
    attendance,
    study_hours
):
    records = _records(collection)

    if len(records) < 20:
        raise ValueError(
            "At least 20 complete records are needed to train the model."
        )

    X = np.array([
        [float(r[k]) for k in FEATURES]
        for r in records
    ])

    y = np.array([
        float(r[TARGET])
        for r in records
    ])

    model = LinearRegression()
    model.fit(X, y)

    prediction = float(
        model.predict([[
            previous_marks,
            assignment_marks,
            attendance,
            study_hours
        ]])[0]
    )

    return round(max(0, min(100, prediction)), 2)
