# gui_capstone_full_corrected.py
import json
import uuid
from datetime import datetime, timedelta
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import csv
import re
import winsound  # for alert sound on Windows

# ---------------- Constants ----------------
TASK_FILE = "tasks.json"
REMINDER_INTERVAL = 5  # seconds for demo pop-ups

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
    messagebox.showinfo("Export", "Tasks exported to tasks.csv successfully!")

# ---------------- Mock AI Parser ----------------
def parse_task_input(text):
    description = text
    minutes = 10  # default due time
    category = "Work"
    priority = "Medium"
    recurrence = "None"

    time_match = re.search(r'(\d+)\s*minute', text, re.IGNORECASE)
    if time_match:
        minutes = int(time_match.group(1))
    hour_match = re.search(r'(\d+)\s*hour', text, re.IGNORECASE)
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

# ---------------- GUI Class ----------------
class CapstoneGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🧠 Capstone AI Task & Reminder Agent")
        self.tasks = load_tasks()

        # Reminder control
        self.reminder_running = False
        self.reminder_thread = None
        self.stop_event = threading.Event()

        # ---------------- Input Frame ----------------
        input_frame = tk.Frame(root)
        input_frame.pack(pady=10)

        tk.Label(input_frame, text="Enter Task:").grid(row=0, column=0, sticky="w")
        self.task_entry = tk.Entry(input_frame, width=50)
        self.task_entry.grid(row=0, column=1, columnspan=3, sticky="we")

        tk.Label(input_frame, text="Reminder (min):").grid(row=1, column=0, sticky="w")
        self.minutes_entry = tk.Entry(input_frame, width=5)
        self.minutes_entry.insert(0, "10")
        self.minutes_entry.grid(row=1, column=1, sticky="w")

        tk.Label(input_frame, text="Recurrence:").grid(row=1, column=2, sticky="w")
        self.recur_var = tk.StringVar(value="None")
        recur_menu = ttk.Combobox(
            input_frame, textvariable=self.recur_var,
            values=["None","Daily","Weekly","Monthly"], width=12, state="readonly"
        )
        recur_menu.grid(row=1, column=3, sticky="w")

        # ---------------- Buttons ----------------
        button_frame = tk.Frame(root)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Add Task", command=self.add_task).grid(row=0, column=0, padx=5)
        tk.Button(button_frame, text="Start Reminders", command=self.start_reminders).grid(row=0, column=1, padx=5)
        tk.Button(button_frame, text="Stop Reminders", command=self.stop_reminders).grid(row=0, column=2, padx=5)
        tk.Button(button_frame, text="Export CSV", command=lambda: export_to_csv(self.tasks)).grid(row=0, column=3, padx=5)
        tk.Button(button_frame, text="Delete Completed", command=self.delete_completed).grid(row=0, column=4, padx=5)
        tk.Button(button_frame, text="Add Demo Tasks", command=self.add_demo).grid(row=0, column=5, padx=5)
        tk.Button(button_frame, text="Exit", command=root.quit).grid(row=0, column=6, padx=5)

        # Running status label
        self.status_var = tk.StringVar(value="Reminders: Stopped")
        tk.Label(root, textvariable=self.status_var, fg="gray").pack(pady=(0, 5))

        # ---------------- Task List ----------------
        columns = ("ID","Task","Due Time","Category","Priority","Recurrence","Completed")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", height=12)
        for col in columns:
            self.tree.heading(col, text=col)
            width = 120 if col != "Task" else 220
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.update_task_list()

    # ---------------- Add Task ----------------
    def add_task(self):
        text = self.task_entry.get().strip()
        if not text:
            messagebox.showwarning("Input Error", "Please enter a task.")
            return
        try:
            custom_minutes = int(self.minutes_entry.get())
        except ValueError:
            custom_minutes = 10

        desc, _, category, priority, _ = parse_task_input(text)
        recurrence = self.recur_var.get()
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
        self.tasks.append(task)
        save_tasks(self.tasks)
        self.update_task_list()
        self.task_entry.delete(0, tk.END)

    # ---------------- Update Task List ----------------
    def update_task_list(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for task in self.tasks:
            try:
                time_part = task["due_time"].split("T")[1][:8]
            except Exception:
                time_part = task["due_time"]
            values = (
                task["id"],
                task["description"],
                time_part,
                task["category"],
                task["priority"],
                task.get("recurrence","None"),
                task["completed"]
            )
            self.tree.insert("", tk.END, values=values)

    # ---------------- Reminder Loop ----------------
    def reminder_loop(self):
        while not self.stop_event.is_set():
            now = datetime.now()
            due_tasks = []

            for task in self.tasks:
                try:
                    due_time = datetime.fromisoformat(task["due_time"])
                except Exception:
                    continue

                if not task["completed"] and now >= due_time:
                    due_tasks.append(task)

            if due_tasks:
                try:
                    winsound.Beep(1000, 500)
                except Exception:
                    pass
                self.root.after(0, self.process_due_tasks_ui, [t["id"] for t in due_tasks])

            time.sleep(REMINDER_INTERVAL)

    # ---------------- Process due tasks ----------------
    def process_due_tasks_ui(self, due_task_ids):
        for tid in due_task_ids:
            task = next((t for t in self.tasks if t["id"] == tid), None)
            if not task:
                continue

            self.show_popup(f"Task Due: {task['description']}")
            task["completed"] = True
            due_time = datetime.fromisoformat(task["due_time"])

            rec = task.get("recurrence")
            if rec == "Daily":
                task["completed"] = False
                task["due_time"] = (due_time + timedelta(days=1)).isoformat()
            elif rec == "Weekly":
                task["completed"] = False
                task["due_time"] = (due_time + timedelta(weeks=1)).isoformat()
            elif rec == "Monthly":
                task["completed"] = False
                task["due_time"] = (due_time + timedelta(days=30)).isoformat()

        save_tasks(self.tasks)
        self.update_task_list()
        self.status_var.set(f"Reminders: Running ({len(due_task_ids)} task(s) alerted)")
    # ---------------- Pop-up ----------------
    def show_popup(self, message, duration=3000):
        popup = tk.Toplevel(self.root)
        popup.title("Reminder")
        popup.geometry("320x110+500+200")
        label = tk.Label(popup, text=message, font=("Arial", 12), fg="blue", wraplength=280)
        label.pack(expand=True, padx=10, pady=10)
        # Auto-close after duration (milliseconds)
        popup.after(duration, popup.destroy)

    # ---------------- Start / Stop Reminders ----------------
    def start_reminders(self):
        if self.reminder_running:
            messagebox.showinfo("Reminders", "Auto reminders already running.")
            return
        self.reminder_running = True
        self.stop_event.clear()
        self.reminder_thread = threading.Thread(target=self.reminder_loop, daemon=True)
        self.reminder_thread.start()
        self.status_var.set("Reminders: Running")
        messagebox.showinfo("Reminders", "Auto reminders started!")

    def stop_reminders(self):
        if not self.reminder_running:
            messagebox.showinfo("Reminders", "Auto reminders already stopped.")
            return
        self.reminder_running = False
        self.stop_event.set()
        self.status_var.set("Reminders: Stopped")
        messagebox.showinfo("Reminders", "Auto reminders stopped!")

    # ---------------- Delete Completed ----------------
    def delete_completed(self):
        completed_tasks = [t for t in self.tasks if t["completed"]]
        if not completed_tasks:
            messagebox.showinfo("Delete", "No completed tasks to delete.")
            return
        self.tasks = [t for t in self.tasks if not t["completed"]]
        save_tasks(self.tasks)
        self.update_task_list()
        messagebox.showinfo("Delete", "Completed tasks deleted.")

    # ---------------- Add Demo Tasks ----------------
    def add_demo(self):
        demo_texts = [
            "Demo: Submit Capstone in 1 minute",
            "Demo: Call friend in 2 minute"
        ]
        for t_text in demo_texts:
            self.task_entry.delete(0, tk.END)
            self.task_entry.insert(0, t_text)
            self.add_task()
        messagebox.showinfo("Demo", "2 Demo tasks added!")

# ---------------- Main ----------------
if __name__ == "__main__":
    root = tk.Tk()
    app = CapstoneGUI(root)
    root.mainloop()
