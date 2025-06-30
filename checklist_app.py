import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry
import sqlite3
from datetime import date, timedelta, datetime

DB_FILE = "zenchecklist.db"
TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            date TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            category TEXT DEFAULT 'General',
            order_index INTEGER DEFAULT 0,
            recurrence TEXT DEFAULT 'none'
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


def migrate_schema():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for column in ["category TEXT DEFAULT 'General'",
                   "order_index INTEGER DEFAULT 0",
                   "recurrence TEXT DEFAULT 'none'"]:
        try:
            c.execute(f"ALTER TABLE tasks ADD COLUMN {column}")
        except:
            pass
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


def apply_recurring_tasks():
    today_obj = date.today()
    today_iso = today_obj.isoformat()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT task, category, recurrence FROM tasks WHERE recurrence != 'none'")
    tasks = c.fetchall()

    for task, category, recurrence in tasks:
        c.execute("SELECT COUNT(*) FROM tasks WHERE task = ? AND date = ?", (task, today_iso))
        if c.fetchone()[0] > 0:
            continue

        if recurrence == "daily":
            should_add = True
        elif recurrence == "weekly":
            created_date = YESTERDAY  # assume added yesterday for comparison
            should_add = date.fromisoformat(created_date).weekday() == today_obj.weekday()
        elif recurrence == "monthly":
            should_add = True if today_obj.day == 1 else False  # simplify: every 1st of month
        else:
            should_add = False

        if should_add:
            c.execute("INSERT INTO tasks (task, date, completed, category, recurrence) VALUES (?, ?, 0, ?, ?)",
                      (task, today_iso, category, recurrence))

    conn.commit()
    conn.close()


class ZenChecklistApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ZenChecklist")
        self.root.geometry("720x800")

        self.task_entry = tk.Entry(root)
        self.task_entry.pack(fill="x", padx=10, pady=(10, 0))

        # Category dropdown
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

        # Recurrence dropdown
        tk.Label(category_frame, text="Repeat:").pack(anchor="w", pady=(10, 0))
        self.recurrence_var = tk.StringVar()
        self.recurrence_combo = ttk.Combobox(category_frame, textvariable=self.recurrence_var, state="readonly")
        self.recurrence_combo['values'] = ("none", "daily", "weekly", "monthly")
        self.recurrence_combo.current(0)
        self.recurrence_combo.pack(fill="x")

        # Date selector
        tk.Label(category_frame, text="Task Date:").pack(anchor="w", pady=(10, 0))
        self.task_date_picker = DateEntry(category_frame, width=12, date_pattern='yyyy-mm-dd')
        self.task_date_picker.pack(anchor="w")

        self.add_button = tk.Button(root, text="Add Task", command=self.add_task)
        self.add_button.pack(padx=10, pady=5, anchor="w")

        # Panels
        task_panels = tk.Frame(root)
        task_panels.pack(fill="both", expand=True, padx=10)

        # Left: To Do (Listbox)
        self.todo_frame = tk.LabelFrame(task_panels, text="To Do")
        self.todo_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.todo_listbox = tk.Listbox(self.todo_frame, selectmode=tk.MULTIPLE)
        self.todo_listbox.pack(fill="both", expand=True)
        self.todo_listbox.bind("<B1-Motion>", self.drag_task)
        self.todo_listbox.bind("<ButtonRelease-1>", self.drop_task)

        # Right: Done (Checkbuttons)
        self.done_frame = tk.LabelFrame(task_panels, text="Done")
        self.done_frame.pack(side="right", fill="both", expand=True)
        self.task_vars = {}

        control_frame = tk.Frame(root)
        control_frame.pack(fill="x", padx=10)
        tk.Button(control_frame, text="Done", command=self.mark_tasks_done).pack(side="left", padx=(0, 5))
        tk.Button(control_frame, text="Remove", command=self.remove_tasks).pack(side="left")

        # Protein Tracker
        protein_frame = tk.LabelFrame(root, text="Protein Tracker")
        protein_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(protein_frame, text="Protein consumed today (g):").pack(anchor="w")
        self.protein_entry = tk.Entry(protein_frame, width=10)
        self.protein_entry.pack(anchor="w")
        tk.Button(protein_frame, text="Save", command=self.save_protein).pack(anchor="w", pady=5)
        self.protein_status = tk.Label(protein_frame, text="")
        self.protein_status.pack(anchor="w")
        self.load_protein()

        # View by Date
        view_frame = tk.LabelFrame(root, text="View Tasks for a Specific Date")
        view_frame.pack(fill="both", padx=10, pady=5)
        tk.Label(view_frame, text="Select a date:").pack(anchor="w")
        self.view_date_picker = DateEntry(view_frame, width=12, date_pattern='yyyy-mm-dd')
        self.view_date_picker.pack(anchor="w", pady=(0, 5))
        tk.Button(view_frame, text="Show Tasks", command=self.show_tasks_for_date).pack(anchor="w", pady=5)
        self.view_output = tk.Text(view_frame, height=8)
        self.view_output.pack(fill="both", expand=True)

        carry_forward_incomplete_tasks()
        apply_recurring_tasks()
        self.load_today_tasks()

    def toggle_custom_category(self, event):
        if self.category_var.get() == "Custom":
            self.custom_category_entry.pack(fill="x", pady=5)
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
        recurrence = self.recurrence_var.get()
        task_date = self.task_date_picker.get_date().isoformat()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT MAX(order_index) FROM tasks WHERE date = ?", (task_date,))
        max_order = c.fetchone()[0] or 0
        c.execute("INSERT INTO tasks (task, date, completed, category, order_index, recurrence) VALUES (?, ?, 0, ?, ?, ?)",
                  (task, task_date, category, max_order + 1, recurrence))
        conn.commit()
        conn.close()
        self.task_entry.delete(0, tk.END)
        self.custom_category_entry.delete(0, tk.END)
        if task_date == TODAY:
            self.load_today_tasks()

    def load_today_tasks(self):
        self.todo_listbox.delete(0, tk.END)
        for widget in self.done_frame.winfo_children():
            widget.destroy()
        self.task_vars = {}
        self.task_id_map = {}

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, task, completed, category FROM tasks WHERE date = ? ORDER BY order_index ASC", (TODAY,))
        rows = c.fetchall()
        conn.close()

        for task_id, task_text, completed, category in rows:
            display = f"[{category}] {task_text}"
            if completed:
                var = tk.IntVar()
                cb = tk.Checkbutton(self.done_frame, text=f"[✓] {display}", variable=var)
                cb.pack(anchor="w")
                self.task_vars[task_id] = (var, completed)
            else:
                self.todo_listbox.insert(tk.END, display)
                self.task_id_map[display] = task_id

    def mark_tasks_done(self):
        selected = self.todo_listbox.curselection()
        if not selected:
            return
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        for index in selected:
            label = self.todo_listbox.get(index)
            task_id = self.task_id_map.get(label)
            if task_id:
                c.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        self.load_today_tasks()

    def remove_tasks(self):
        selected = self.todo_listbox.curselection()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        for index in selected:
            label = self.todo_listbox.get(index)
            task_id = self.task_id_map.get(label)
            if task_id:
                c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        for task_id, (var, _) in list(self.task_vars.items()):
            if var.get() == 1:
                c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        self.load_today_tasks()

    def save_protein(self):
        try:
            grams = int(self.protein_entry.get())
        except:
            messagebox.showerror("Error", "Enter a number")
            return
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT grams FROM protein WHERE date = ?", (TODAY,))
        existing = c.fetchone()
        if existing:
            grams += existing[0]
            c.execute("UPDATE protein SET grams = ? WHERE date = ?", (grams, TODAY))
        else:
            c.execute("INSERT INTO protein (date, grams) VALUES (?, ?)", (TODAY, grams))
        conn.commit()
        conn.close()
        self.protein_entry.delete(0, tk.END)
        self.protein_status.config(text=f"Saved: {grams}g")

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
        c.execute("SELECT task, completed, category, recurrence FROM tasks WHERE date = ?", (selected_date,))
        tasks = c.fetchall()
        conn.close()
        output = f"Tasks on {selected_date}:\n"
        for task, completed, category, recurrence in tasks:
            prefix = "[✓] " if completed else ""
            output += f"{prefix}[{category}][{recurrence}] {task}\n"
        if not tasks:
            output += "No tasks found."
        self.view_output.delete("1.0", tk.END)
        self.view_output.insert(tk.END, output)

    def drag_task(self, event):
        widget = event.widget
        index = widget.nearest(event.y)
        widget.selection_clear(0, tk.END)
        widget.selection_set(index)

    def drop_task(self, event):
        widget = event.widget
        selected = widget.curselection()
        if not selected:
            return
        index = selected[0]
        new_index = widget.nearest(event.y)
        if new_index != index:
            label = widget.get(index)
            widget.delete(index)
            widget.insert(new_index, label)
            self.update_task_order()

    def update_task_order(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        for i in range(self.todo_listbox.size()):
            label = self.todo_listbox.get(i)
            task_id = self.task_id_map.get(label)
            if task_id:
                c.execute("UPDATE tasks SET order_index = ? WHERE id = ?", (i, task_id))
        conn.commit()
        conn.close()


if __name__ == "__main__":
    init_db()
    migrate_schema()
    root = tk.Tk()
    app = ZenChecklistApp(root)
    root.mainloop()
