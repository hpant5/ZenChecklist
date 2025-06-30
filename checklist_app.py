import tkinter as tk
from tkinter import messagebox
from tkcalendar import DateEntry
import sqlite3
from datetime import date

DB_FILE = "zenchecklist.db"
TODAY = date.today().isoformat()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            date TEXT NOT NULL,
            completed INTEGER DEFAULT 0
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

class ZenChecklistApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ZenChecklist")
        self.root.geometry("550x720")

        # --- Task Entry ---
        self.task_entry = tk.Entry(root)
        self.task_entry.pack(fill="x", padx=10, pady=(10, 0))

        # --- Calendar for Add Task Date ---
        date_frame = tk.Frame(root)
        date_frame.pack(fill="x", padx=10)
        tk.Label(date_frame, text="Task Date (default is today):").pack(anchor="w")
        self.task_date_picker = DateEntry(date_frame, width=12, background='darkblue',
                                          foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.task_date_picker.pack(anchor="w", pady=(0, 5))

        # --- Buttons for Add/Remove ---
        button_frame = tk.Frame(root)
        button_frame.pack(fill="x", padx=10, pady=(5, 5))

        self.add_button = tk.Button(button_frame, text="Add Task", command=self.add_task)
        self.add_button.pack(side="left", padx=(0, 5))

        self.remove_button = tk.Button(button_frame, text="Remove Selected Task", command=self.remove_selected_task)
        self.remove_button.pack(side="left")

        # --- Task List (Today) ---
        task_list_frame = tk.LabelFrame(root, text="Today's Tasks", padx=10, pady=10)
        task_list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.task_listbox = tk.Listbox(task_list_frame, selectmode=tk.SINGLE)
        self.task_listbox.pack(fill="both", expand=True)
        self.task_id_map = {}
        self.load_today_tasks()

        # --- Protein Tracker ---
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

        # --- View Tasks for Any Date ---
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

    def add_task(self):
        task = self.task_entry.get().strip()
        if not task:
            messagebox.showwarning("Input Error", "Task cannot be empty.")
            return

        task_date = self.task_date_picker.get_date().isoformat()

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO tasks (task, date) VALUES (?, ?)", (task, task_date))
        conn.commit()
        conn.close()
        self.task_entry.delete(0, tk.END)

        if task_date == TODAY:
            self.load_today_tasks()

    def remove_selected_task(self):
        selection = self.task_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a task to remove.")
            return
        index = selection[0]
        task_text = self.task_listbox.get(index)
        task_id = self.task_id_map.get(task_text)
        if task_id:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            conn.close()
            self.load_today_tasks()

    def load_today_tasks(self):
        self.task_listbox.delete(0, tk.END)
        self.task_id_map = {}
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, task FROM tasks WHERE date = ?", (TODAY,))
        rows = c.fetchall()
        conn.close()
        for task_id, task_text in rows:
            self.task_listbox.insert(tk.END, task_text)
            self.task_id_map[task_text] = task_id

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
        if row:
            new_total = row[0] + added_grams
            c.execute("UPDATE protein SET grams = ? WHERE date = ?", (new_total, TODAY))
        else:
            new_total = added_grams
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
        if row:
            self.protein_entry.delete(0, tk.END)
            self.protein_entry.insert(0, str(row[0]))
            self.protein_status.config(text=f"Saved: {row[0]}g")
        conn.close()

    def show_tasks_for_date(self):
        selected_date = self.view_date_picker.get_date().isoformat()

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT task FROM tasks WHERE date = ?", (selected_date,))
        tasks = c.fetchall()
        conn.close()

        output = f"Tasks on {selected_date}:\n"
        output += "\n".join([f"- {task[0]}" for task in tasks]) or "No tasks found."
        self.view_output.delete("1.0", tk.END)
        self.view_output.insert(tk.END, output)

# --- Launch App ---
if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = ZenChecklistApp(root)
    root.mainloop()
