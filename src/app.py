"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import sqlite3
from typing import Dict, Any

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# SQLite DB file path
DB_PATH = current_dir / "data" / "activities.db"
DB_PATH.parent.mkdir(exist_ok=True)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS activities (
            name TEXT PRIMARY KEY,
            description TEXT,
            schedule TEXT,
            max_participants INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS participants (
            activity_name TEXT,
            email TEXT,
            PRIMARY KEY (activity_name, email),
            FOREIGN KEY (activity_name) REFERENCES activities(name) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    conn.close()


def load_activities_from_db() -> Dict[str, Any]:
    conn = get_db_connection()
    cur = conn.cursor()
    activities = {}
    for row in cur.execute("SELECT name, description, schedule, max_participants FROM activities"):
        name = row[0]
        activities[name] = {
            "description": row[1],
            "schedule": row[2],
            "max_participants": row[3],
            "participants": []
        }

    for row in cur.execute("SELECT activity_name, email FROM participants"):
        activity_name, email = row
        if activity_name in activities:
            activities[activity_name]["participants"].append(email)
    conn.close()
    return activities


def save_activity_to_db(name: str, activity: Dict[str, Any]):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "REPLACE INTO activities (name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
        (name, activity.get("description", ""), activity.get("schedule", ""), activity.get("max_participants", 0)),
    )
    conn.commit()
    conn.close()


def add_participant_db(activity_name: str, email: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO participants (activity_name, email) VALUES (?, ?)",
        (activity_name, email),
    )
    conn.commit()
    conn.close()


def remove_participant_db(activity_name: str, email: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM participants WHERE activity_name = ? AND email = ?",
        (activity_name, email),
    )
    conn.commit()
    conn.close()


# Initialize DB and load activities into memory cache
init_db()
activities = load_activities_from_db()

# If DB is empty, populate with some sample activities
if not activities:
    activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    }
    # persist these sample activities
    for name, act in activities.items():
        save_activity_to_db(name, act)
        for p in act.get("participants", []):
            add_participant_db(name, p)


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    # persist participant
    add_participant_db(activity_name, email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    # persist removal
    remove_participant_db(activity_name, email)
    return {"message": f"Unregistered {email} from {activity_name}"}
