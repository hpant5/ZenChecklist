import tkinter as tk
from tkinter import messagebox
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
        self.root.geometry("500x600")

        task_frame = tk.LabelFrame(root, text="Today's Tasks", padx=10, pady=10)
        task_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.task_entry = tk.Entry(root)
        self.task_entry.pack(fill="x", padx=10, pady=(0, 5))

        add_button = tk.Button(root, text="Add Task", command=self.add_task)
        add_button.pack(padx=10, pady=(0, 5))

        self.task_list_frame = task_frame
        self.task_checkbuttons = []
        self.load_today_tasks()


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

        history_frame = tk.LabelFrame(root, text="History View", padx=10, pady=10)
        history_frame.pack(fill="both", expand=True, padx=10, pady=5)

        tk.Label(history_frame, text="Enter date (YYYY-MM-DD):").pack(anchor="w")
        self.date_selector = tk.Entry(history_frame)
        self.date_selector.pack(anchor="w")
        history_button = tk.Button(history_frame, text="Show", command=self.show_history)
        history_button.pack(anchor="w", pady=5)
        self.history_output = tk.Text(history_frame, height=8)
        self.history_output.pack(fill="both", expand=True)

    def add_task(self):
        task = self.task_entry.get().strip()
        if not task:
            messagebox.showwarning("Input Error", "Task cannot be empty.")
            return
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO tasks (task, date) VALUES (?, ?)", (task, TODAY))
        conn.commit()
        conn.close()
        self.task_entry.delete(0, tk.END)
        self.load_today_tasks()

    def load_today_tasks(self):
        for widget in self.task_list_frame.winfo_children():
            widget.destroy()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT task FROM tasks WHERE date = ?", (TODAY,))
        rows = c.fetchall()
        conn.close()
        for row in rows:
            cb = tk.Checkbutton(self.task_list_frame, text=row[0])
            cb.pack(anchor="w")
            self.task_checkbuttons.append(cb)

    def save_protein(self):
        try:
            grams = int(self.protein_entry.get())
        except ValueError:
            messagebox.showerror("Input Error", "Please enter a valid number.")
            return
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO protein (date, grams) VALUES (?, ?)", (TODAY, grams))
        conn.commit()
        conn.close()
        self.protein_status.config(text=f"Saved: {grams}g")

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

    def show_history(self):
        selected_date = self.date_selector.get().strip()
        if not selected_date:
            messagebox.showwarning("Input Error", "Please enter a date.")
            return
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT task FROM tasks WHERE date = ?", (selected_date,))
        tasks = c.fetchall()
        c.execute("SELECT grams FROM protein WHERE date = ?", (selected_date,))
        protein = c.fetchone()
        conn.close()
        output = f"Tasks on {selected_date}:\n"
        output += "\n".join([f"- {task[0]}" for task in tasks]) or "No tasks found."
        output += "\n\nProtein consumed: "
        output += f"{protein[0]}g" if protein else "No data."
        self.history_output.delete("1.0", tk.END)
        self.history_output.insert(tk.END, output)


if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = ZenChecklistApp(root)
    root.mainloop()
