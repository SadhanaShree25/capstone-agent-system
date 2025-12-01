# streamlit_capstone_autoreminder.py
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
            writer.writerow([
                t["id"], t["description"], t["due_time"], t["category"],
                t["priority"], t.get("recurrence","None"), t["completed"]
            ])
    st.success("Tasks exported to tasks.csv")

# ---------------- Mock AI Parser ----------------
def parse_task_input(text):
    description = text
    minutes = 10  # default due time
    category = "Work"
    priority = "Medium"
    recurrence = "None"

    time_match = re.search(r'(\d+)\s*minute', text)
    if time_match:
        minutes = int(time_match.group(1))
    if "hour" in text.lower():
        hour_match = re.search(r'(\d+)\s*hour', text)
        if hour_match:
            minutes = int(hour_match.group(1)) * 60
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
st.title("🧠 Capstone AI Task & Reminder Agent (Web Version)")

tasks = load_tasks()

# ---------------- Auto Refresh for Real-Time Reminders ----------------
# Refresh every 10 seconds
st_autorefresh(interval=10 * 1000, key="auto_refresh")

# ---------------- Add New Task ----------------
with st.expander("Add New Task"):
    task_text = st.text_input("Enter Task (natural language):")
    custom_minutes = st.number_input("Set Reminder in minutes:", min_value=1, value=10)
    recurrence = st.selectbox("Recurrence", ["None","Daily","Weekly","Monthly"])
    add_button = st.button("Add Task")

if add_button and task_text:
    desc, _, category, priority, _ = parse_task_input(task_text)
    task_id = str(uuid.uuid4())
    due_time = (datetime.now() + timedelta(minutes=custom_minutes)).isoformat()
    task = {
        "id": task_id,
        "description": desc,
        "due_time": due_time,
        "category": category,
        "priority": priority,
        "recurrence": recurrence,
        "completed": False
    }
    tasks.append(task)
    save_tasks(tasks)
    st.success(f"Task added: {desc} | Reminder in {custom_minutes} minutes")

# ---------------- Task List ----------------
st.subheader("📋 Task List")
if tasks:
    for t in tasks:
        status = "✅ Done" if t["completed"] else "⏳ Pending"
        st.write(f"**{t['description']}** | Due: {t['due_time'].split('T')[1][:8]} | Category: {t['category']} | Priority: {t['priority']} | Recurrence: {t.get('recurrence','None')} | Status: {status}")
else:
    st.write("No tasks added yet.")

# ---------------- Auto Reminder Check ----------------
def check_reminders_auto():
    now = datetime.now()
    triggered = False
    for task in tasks:
        due_time = datetime.fromisoformat(task["due_time"])
        if not task["completed"] and now >= due_time:
            st.balloons()
            st.info(f"🔔 Task Due: {task['description']}")
            task["completed"] = True
            triggered = True
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
    if triggered:
        save_tasks(tasks)

check_reminders_auto()

# ---------------- Export CSV ----------------
if st.button("Export Tasks to CSV"):
    export_to_csv(tasks)

# ---------------- Delete Completed Task ----------------
st.subheader("🗑️ Delete Completed Tasks")
completed_tasks = [t for t in tasks if t["completed"]]
if completed_tasks:
    task_to_delete = st.selectbox("Select Task to Delete:", [t["description"] for t in completed_tasks])
    if st.button("Delete Task"):
        tasks[:] = [t for t in tasks if t["description"] != task_to_delete]
        save_tasks(tasks)
        st.success(f"Deleted task: {task_to_delete}")
else:
    st.write("No completed tasks to delete.")
