import tkinter as tk
from tkinter import messagebox
import json
import os
from datetime import datetime

TASKS = [
    "Put the nuts and seeds for the day in the lunch box",
    "Take the water out for the day",
    "Write the task (DSA, ML, SQL, DE) for the day",
    "100 grips each hand",
    "90 push-ups (20, 30, 40 reps)",
    "Gym session for the day",
    "Protein for the day",
    "Cardio for the day",
    "Devpost hackathon",
    "Apply for the job",
    "Morning Routine: 1 carrot, 15g pumpkin seeds, 1 scoop whey protein, 5g creatine",
    "Mid-morning Snack: 10 almonds, 5 pistachios, 5 peanuts",
    "Lunch: 2 slices whole wheat bread, 1 cheese slice, 150g curd",
    "Afternoon Snack: 1 carrot, 10g cashews, 5g pecans",
    "Evening: Banana + Whey protein + Water",
    "Dinner: 1 cup legumes (rajma/chickpeas), curd (optional)"
]
DATA_FILE = "checklist_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                data = json.load(f)
                if data.get("date") != datetime.today().strftime('%Y-%m-%d'):
                    return {"tasks": [False]*len(TASKS), "protein": 0, "date": datetime.today().strftime('%Y-%m-%d')}
                return data
            except json.JSONDecodeError:
                return {"tasks": [False]*len(TASKS), "protein": 0, "date": datetime.today().strftime('%Y-%m-%d')}
    else:
        return {"tasks": [False]*len(TASKS), "protein": 0, "date": datetime.today().strftime('%Y-%m-%d')}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(app_data, f)

def update_task(index):
    app_data["tasks"][index] = task_vars[index].get()
    save_data()

def add_protein():
    try:
        val = int(protein_entry.get())
        app_data["protein"] += val
        protein_total_label.config(text=f"Total Protein Today: {app_data['protein']}g")
        protein_entry.delete(0, tk.END)
        save_data()
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter a valid number.")


app_data = load_data()
root = tk.Tk()
root.title("Daily Checklist")
root.geometry("600x700")
root.resizable(False, False)


task_vars = []
tk.Label(root, text="Your Daily Tasks:", font=('Arial', 14, 'bold')).pack(pady=10)
for i, task in enumerate(TASKS):
    var = tk.BooleanVar(value=app_data["tasks"][i])
    chk = tk.Checkbutton(root, text=task, variable=var, command=lambda i=i: update_task(i), wraplength=580, anchor='w', justify='left')
    chk.pack(anchor='w', padx=20)
    task_vars.append(var)


tk.Label(root, text="\nTrack Your Protein Intake (grams):", font=('Arial', 12)).pack()
protein_entry = tk.Entry(root)
protein_entry.pack(pady=5)
tk.Button(root, text="Submit", command=add_protein).pack()
protein_total_label = tk.Label(root, text=f"Total Protein Today: {app_data['protein']}g", font=('Arial', 10, 'italic'))
protein_total_label.pack(pady=5)

root.mainloop()