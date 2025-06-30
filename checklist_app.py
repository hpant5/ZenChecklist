import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry
import sqlite3
from datetime import date, timedelta
import os

DB_FILE = "zenchecklist.db"
TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


def migrate_schema():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Try adding category column if it doesn't exist
    try:
        c.execute("ALTER TABLE tasks ADD COLUMN category TEXT DEFAULT 'General'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.close()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Extend schema to support category
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            date TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            category TEXT DEFAULT 'General'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS protein (
            date TEXT PRIMARY KEY,
            grams INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()


def carry_forward_incomplete_tasks():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT task, category FROM tasks WHERE date = ? AND completed = 0", (YESTERDAY,))
    tasks = c.fetchall()
    for task, category in tasks:
        c.execute("SELECT COUNT(*) FROM tasks WHERE task = ? AND date = ?", (task, TODAY))
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO tasks (task, date, completed, category) VALUES (?, ?, 0, ?)", (task, TODAY, category))
    conn.commit()
    conn.close()


class ZenChecklistApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ZenChecklist")
        self.root.geometry("720x780")

        # Task Entry
        self.task_entry = tk.Entry(root)
        self.task_entry.pack(fill="x", padx=10, pady=(10, 0))

        # Category Selector
        category_frame = tk.Frame(root)
        category_frame.pack(fill="x", padx=10)

        tk.Label(category_frame, text="Select Category:").pack(anchor="w")
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(category_frame, textvariable=self.category_var, state="readonly")
        self.category_combo['values'] = ("Work", "Personal", "Health", "Custom")
        self.category_combo.current(0)
        self.category_combo.pack(fill="x")

        self.custom_category_entry = tk.Entry(category_frame)
        self.category_combo.bind("<<ComboboxSelected>>", self.toggle_custom_category)

        # Date Picker
        date_frame = tk.Frame(root)
        date_frame.pack(fill="x", padx=10)
        tk.Label(date_frame, text="Task Date (default is today):").pack(anchor="w")
        self.task_date_picker = DateEntry(date_frame, width=12, background='darkblue',
                                          foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.task_date_picker.pack(anchor="w", pady=(0, 5))

        # Add Button
        self.add_button = tk.Button(root, text="Add Task", command=self.add_task)
        self.add_button.pack(padx=10, pady=(0, 5), anchor="w")

        # Task Frames
        task_panels = tk.Frame(root)
        task_panels.pack(fill="both", expand=True, padx=10, pady=5)

        self.todo_frame = tk.LabelFrame(task_panels, text="To Do", padx=10, pady=10)
        self.todo_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        self.done_frame = tk.LabelFrame(task_panels, text="Done", padx=10, pady=10)
        self.done_frame.pack(side="right", fill="both", expand=True)

        # Task Controls
        control_frame = tk.Frame(root)
        control_frame.pack(fill="x", padx=10, pady=5)

        tk.Button(control_frame, text="Done", command=self.mark_tasks_done).pack(side="left", padx=(0, 5))
        tk.Button(control_frame, text="Remove", command=self.remove_tasks).pack(side="left")

        # Protein Tracker
        protein_frame = tk.LabelFrame(root, text="Protein Tracker", padx=10, pady=10)
        protein_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(protein_frame, text="Protein consumed today (g):").pack(anchor="w")
        self.protein_entry = tk.Entry(protein_frame, width=10)
        self.protein_entry.pack(anchor="w")
        save_button = tk.Button(protein_frame, text="Save", command=self.save_protein)
        save_button.pack(anchor="w", pady=5)
        self.protein_status = tk.Label(protein_frame, text="")
        self.protein_status.pack(anchor="w")
        self.load_protein()

        # View Any Date
        view_frame = tk.LabelFrame(root, text="View Tasks for a Specific Date", padx=10, pady=10)
        view_frame.pack(fill="both", expand=True, padx=10, pady=5)

        tk.Label(view_frame, text="Select a date:").pack(anchor="w")
        self.view_date_picker = DateEntry(view_frame, width=12, background='darkblue',
                                          foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.view_date_picker.pack(anchor="w", pady=(0, 5))

        view_button = tk.Button(view_frame, text="Show Tasks", command=self.show_tasks_for_date)
        view_button.pack(anchor="w", pady=5)

        self.view_output = tk.Text(view_frame, height=8)
        self.view_output.pack(fill="both", expand=True)

        carry_forward_incomplete_tasks()
        self.load_today_tasks()

    def toggle_custom_category(self, event):
        selected = self.category_var.get()
        if selected == "Custom":
            self.custom_category_entry.pack(fill="x", padx=0, pady=5)
        else:
            self.custom_category_entry.pack_forget()

    def get_category(self):
        category = self.category_var.get()
        if category == "Custom":
            custom = self.custom_category_entry.get().strip()
            return custom if custom else "General"
        return category

    def add_task(self):
        task = self.task_entry.get().strip()
        if not task:
            messagebox.showwarning("Input Error", "Task cannot be empty.")
            return
        category = self.get_category()
        task_date = self.task_date_picker.get_date().isoformat()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO tasks (task, date, completed, category) VALUES (?, ?, 0, ?)", (task, task_date, category))
        conn.commit()
        conn.close()
        self.task_entry.delete(0, tk.END)
        self.custom_category_entry.delete(0, tk.END)
        if task_date == TODAY:
            self.load_today_tasks()

    def load_today_tasks(self):
        for widget in self.todo_frame.winfo_children():
            widget.destroy()
        for widget in self.done_frame.winfo_children():
            widget.destroy()
        self.task_vars = {}

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, task, completed, category FROM tasks WHERE date = ?", (TODAY,))
        rows = c.fetchall()
        conn.close()

        for task_id, task_text, completed, category in rows:
            var = tk.IntVar()
            display = f"[{category}] {task_text}"
            frame = self.done_frame if completed else self.todo_frame
            cb = tk.Checkbutton(frame, text=display, variable=var)
            cb.pack(anchor="w")
            self.task_vars[task_id] = (var, completed)

    def mark_tasks_done(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        for task_id, (var, completed) in self.task_vars.items():
            if var.get() == 1 and not completed:
                c.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        self.load_today_tasks()

    def remove_tasks(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        for task_id, (var, _) in self.task_vars.items():
            if var.get() == 1:
                c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        self.load_today_tasks()

    def save_protein(self):
        try:
            added_grams = int(self.protein_entry.get())
        except ValueError:
            messagebox.showerror("Input Error", "Please enter a valid number.")
            return
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT grams FROM protein WHERE date = ?", (TODAY,))
        row = c.fetchone()
        new_total = added_grams
        if row:
            new_total += row[0]
            c.execute("UPDATE protein SET grams = ? WHERE date = ?", (new_total, TODAY))
        else:
            c.execute("INSERT INTO protein (date, grams) VALUES (?, ?)", (TODAY, new_total))
        conn.commit()
        conn.close()
        self.protein_entry.delete(0, tk.END)
        self.protein_status.config(text=f"Saved: {new_total}g")

    def load_protein(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT grams FROM protein WHERE date = ?", (TODAY,))
        row = c.fetchone()
        conn.close()
        if row:
            self.protein_entry.delete(0, tk.END)
            self.protein_entry.insert(0, str(row[0]))
            self.protein_status.config(text=f"Saved: {row[0]}g")

    def show_tasks_for_date(self):
        selected_date = self.view_date_picker.get_date().isoformat()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT task, completed, category FROM tasks WHERE date = ?", (selected_date,))
        tasks = c.fetchall()
        conn.close()

        output = f"Tasks on {selected_date}:\n"
        for task, completed, category in tasks:
            mark = "[✓] " if completed else ""
            output += f"{mark}[{category}] {task}\n"
        if not tasks:
            output += "No tasks found."
        self.view_output.delete("1.0", tk.END)
        self.view_output.insert(tk.END, output)


if __name__ == "__main__":
    init_db()
    migrate_schema()  
    root = tk.Tk()
    app = ZenChecklistApp(root)
    root.mainloop()

