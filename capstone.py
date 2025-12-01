# gui_capstone_full.py
import json
import uuid
from datetime import datetime, timedelta
import threading
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

# ---------------- GUI Class ----------------
class CapstoneGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🧠 Capstone AI Task & Reminder Agent")
        self.tasks = load_tasks()
        self.reminder_running = False
        self.reminder_thread = None

        # ---------------- Input Frame ----------------
        input_frame = tk.Frame(root)
        input_frame.pack(pady=10)

        tk.Label(input_frame, text="Enter Task:").grid(row=0, column=0)
        self.task_entry = tk.Entry(input_frame, width=50)
        self.task_entry.grid(row=0, column=1, columnspan=3)

        tk.Label(input_frame, text="Reminder (min):").grid(row=1, column=0)
        self.minutes_entry = tk.Entry(input_frame, width=5)
        self.minutes_entry.insert(0, "10")
        self.minutes_entry.grid(row=1, column=1)

        tk.Label(input_frame, text="Recurrence:").grid(row=1, column=2)
        self.recur_var = tk.StringVar(value="None")
        recur_menu = ttk.Combobox(input_frame, textvariable=self.recur_var,
                                  values=["None","Daily","Weekly","Monthly"], width=12)
        recur_menu.grid(row=1, column=3)

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

        # ---------------- Task List ----------------
        columns = ("ID","Task","Due Time","Category","Priority","Recurrence","Completed")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", height=12)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        self.tree.pack()
        self.update_task_list()

    # ---------------- Add Task ----------------
    def add_task(self):
        text = self.task_entry.get()
        if not text:
            messagebox.showwarning("Input Error", "Please enter a task.")
            return
        try:
            custom_minutes = int(self.minutes_entry.get())
        except:
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
            values = (
                task["id"],
                task["description"],
                task["due_time"].split("T")[1][:8],
                task["category"],
                task["priority"],
                task.get("recurrence","None"),
                task["completed"]
            )
            self.tree.insert("", tk.END, values=values)

    # ---------------- Reminder Loop ----------------
    def reminder_loop(self):
        while self.reminder_running:
            now = datetime.now()
            for task in self.tasks:
                due_time = datetime.fromisoformat(task["due_time"])
                if not task["completed"] and now >= due_time:
                    winsound.Beep(1000, 500)  # sound alert
                    self.show_popup(f"Task Due: {task['description']}")
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
            save_tasks(self.tasks)
            self.update_task_list()
            threading.Event().wait(REMINDER_INTERVAL)

    # ---------------- Pop-up ----------------
    def show_popup(self, message, duration=3000):
        popup = tk.Toplevel()
        popup.title("Reminder")
        popup.geometry("300x100+500+200")
        tk.Label(popup, text=message, font=("Arial", 12), fg="blue").pack(expand=True)
        popup.after(duration, popup.destroy)

    # ---------------- Start / Stop Reminders ----------------
    def start_reminders(self):
        if not self.reminder_running:
            self.reminder_running = True
            self.reminder_thread = threading.Thread(target=self.reminder_loop, daemon=True)
            self.reminder_thread.start()
            messagebox.showinfo("Reminders", "Auto reminders started!")

    def stop_reminders(self):
        self.reminder_running = False
        messagebox.showinfo("Reminders", "Auto reminders stopped!")

    # ---------------- Delete Completed ----------------
    def delete_completed(self):
        completed_tasks = [t for t in self.tasks if t["completed"]]
        if not completed_tasks:
            messagebox.showinfo("Delete", "No completed tasks to delete.")
            return
        for t in completed_tasks:
            self.tasks.remove(t)
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
