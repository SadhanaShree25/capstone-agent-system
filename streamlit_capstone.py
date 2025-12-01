# streamlit_capstone.py
import streamlit as st
import json
import uuid
from datetime import datetime, timedelta
import csv
import re
from streamlit_autorefresh import st_autorefresh


# ---------------- Constants ----------------
TASK_FILE = "tasks.json"

# ---------------- Utility Functions ----------------
def load_tasks():
    try:
        with open(TASK_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_tasks(tasks):
    with open(TASK_FILE, "w") as f:
        json.dump(tasks, f, indent=4)

def export_to_csv(tasks):
    with open("tasks.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID","Task","Due Time","Category","Priority","Recurrence","Completed"])
        for t in tasks:
            writer.writerow([t["id"], t["description"], t["due_time"], t["category"], t["priority"], t.get("recurrence","None"), t["completed"]])
    st.success("Tasks exported to tasks.csv")

# ---------------- Mock AI Parser ----------------
def parse_task_input(text):
    description = text
    minutes = 10
    category = "Work"
    priority = "Medium"
    recurrence = "None"

    time_match = re.search(r'(\d+(\.\d+)?)\s*minute', text)
    if time_match:
        minutes = float(time_match.group(1))
    if "tomorrow" in text.lower():
        minutes = 24*60
    if "urgent" in text.lower() or "important" in text.lower():
        priority = "High"
    if "study" in text.lower():
        category = "Study"
    elif "personal" in text.lower():
        category = "Personal"
    return description, minutes, category, priority, recurrence

# ---------------- Streamlit App ----------------
st.set_page_config(page_title="Capstone AI Task Agent", layout="wide")
st.title("🧠 Capstone AI Task & Reminder Agent (Web Version)")

# Load tasks
tasks = load_tasks()

# ---------------- Task Input ----------------
with st.expander("Add New Task"):
    task_text = st.text_input("Enter Task (natural language):")
    recurrence_option = st.selectbox("Recurrence", ["None","Daily","Weekly","Monthly"])
    add_button = st.button("Add Task")

if add_button and task_text:
    desc, minutes, category, priority, _ = parse_task_input(task_text)
    task_id = str(uuid.uuid4())
    due_time = (datetime.now() + timedelta(minutes=minutes)).isoformat()
    task = {
        "id": task_id,
        "description": desc,
        "due_time": due_time,
        "category": category,
        "priority": priority,
        "recurrence": recurrence_option,
        "completed": False
    }
    tasks.append(task)
    save_tasks(tasks)
    st.success(f"Task added: {desc}")

# ---------------- Clear All Tasks ----------------
if st.button("Clear All Tasks"):
    tasks = []
    save_tasks(tasks)
    st.success("All tasks cleared!")

# ---------------- Task Table ----------------
st.subheader("📋 Task List")
if tasks:
    # Remove duplicate descriptions for display
    seen = set()
    unique_tasks = []
    for t in tasks:
        if t["description"] not in seen:
            unique_tasks.append(t)
            seen.add(t["description"])
    for t in unique_tasks:
        status = "✅ Done" if t["completed"] else "⏳ Pending"
        st.write(f"**{t['description']}** | Due: {t['due_time'].split('T')[1][:8]} | "
                 f"Category: {t['category']} | Priority: {t['priority']} | "
                 f"Recurrence: {t.get('recurrence','None')} | Status: {status}")
else:
    st.write("No tasks added yet.")

# ---------------- Demo Tasks ----------------
if st.button("Run Demo Tasks"):
    tasks = []  # Clear previous tasks
    demo_texts = [
        "Submit Kaggle Capstone in 0.1 minute",
        "Call friend in 0.2 minute",
        "Complete Python notebook in 0.3 minute"
    ]
    for t_text in demo_texts:
        desc, minutes, category, priority, _ = parse_task_input(t_text)
        task_id = str(uuid.uuid4())
        due_time = (datetime.now() + timedelta(minutes=minutes)).isoformat()
        task = {
            "id": task_id,
            "description": desc,
            "due_time": due_time,
            "category": category,
            "priority": priority,
            "recurrence": "None",
            "completed": False
        }
        tasks.append(task)
    save_tasks(tasks)
    st.success("Demo tasks added!")

# ---------------- Export CSV ----------------
if st.button("Export Tasks to CSV"):
    export_to_csv(tasks)

# ---------------- Reminder Simulation ----------------
st.subheader("⏰ Reminder Simulation (for Demo)")
import time

def check_reminders():
    now = datetime.now()
    for task in tasks:
        due_time = datetime.fromisoformat(task["due_time"])
        if not task["completed"] and now >= due_time:
            st.balloons()
            st.info(f"🔔 Task Due: {task['description']}")
            task["completed"] = True
            # Handle recurrence
            if task.get("recurrence") == "Daily":
                task["completed"] = False
                task["due_time"] = (due_time + timedelta(days=1)).isoformat()
            elif task.get("recurrence") == "Weekly":
                task["completed"] = False
                task["due_time"] = (due_time + timedelta(weeks=1)).isoformat()
            elif task.get("recurrence") == "Monthly":
                task["completed"] = False
                task["due_time"] = (due_time + timedelta(days=30)).isoformat()
    save_tasks(tasks)

if st.button("Check Reminders"):
    # ---------------- Auto-Refresh for Reminders ----------------
# Auto-refresh every 10 seconds (10000 milliseconds)
    st_autorefresh(interval=10000, key="reminder_autorefresh")



    check_reminders()
    st.success("Reminders checked!")
