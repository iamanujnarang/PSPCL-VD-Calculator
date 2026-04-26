import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import math

def calculate_vd():
    try:
        demand = float(demand_var.get())
        length = float(length_var.get())
        pf = float(pf_var.get())
        cond = conductor_var.get()

        # Conductor R and X values
        data = {
            "Weasel":  {"R": 0.9289, "X": 0.35},
            "Rabbit":  {"R": 0.5524, "X": 0.32},
            "Raccoon": {"R": 0.3712, "X": 0.30},
            "Dog":     {"R": 0.2792, "X": 0.29}
        }
        r = data[cond]["R"]
        x = data[cond]["X"]

        current = (demand * 1000) / (math.sqrt(3) * 11000)
        vd_volts = math.sqrt(3) * current * length * (r * pf + x * math.sin(math.acos(pf)))
        vd_percent = (vd_volts / 11000) * 100

        result_text.set(f"Voltage Drop = {vd_percent:.2f} %")

        if vd_percent <= 5:
            status_text.set("✅ Excellent - Within Limit")
            status_label.config(foreground="green")
        elif vd_percent <= 9:
            status_text.set("⚠️ Acceptable but High")
            status_label.config(foreground="orange")
        else:
            status_text.set("❌ High Drop - Augmentation Recommended")
            status_label.config(foreground="red")

        # Update Graph
        ax.clear()
        ax.bar(["Voltage Drop"], [vd_percent], color='royalblue')
        ax.set_ylabel("Voltage Drop (%)")
        ax.set_title("Voltage Drop Analysis")
        ax.set_ylim(0, max(12, vd_percent + 3))
        canvas.draw()

    except Exception as e:
        messagebox.showerror("Input Error", "Please enter valid numbers!")

# ============== GUI Setup ==============
root = tk.Tk()
root.title("PSPCL 11kV Voltage Drop Calculator")
root.geometry("900x720")
root.configure(bg="#0f172a")

# Title
tk.Label(root, text="⚡ PSPCL 11kV Voltage Drop Calculator", font=("Arial", 20, "bold"), 
         bg="#0f172a", fg="#60a5fa").pack(pady=15)

# Input Frame
frame = ttk.Frame(root, padding=20)
frame.pack(fill="x", padx=30)

ttk.Label(frame, text="Feeder Name:").grid(row=0, column=0, sticky="w", pady=8)
feeder_var = tk.StringVar()
ttk.Entry(frame, textvariable=feeder_var, width=30).grid(row=0, column=1, pady=8)

ttk.Label(frame, text="Maximum Demand (kVA):").grid(row=1, column=0, sticky="w", pady=8)
demand_var = tk.DoubleVar(value=500)
ttk.Entry(frame, textvariable=demand_var, width=30).grid(row=1, column=1, pady=8)

ttk.Label(frame, text="Feeder Length (km):").grid(row=2, column=0, sticky="w", pady=8)
length_var = tk.DoubleVar(value=5.0)
ttk.Entry(frame, textvariable=length_var, width=30).grid(row=2, column=1, pady=8)

ttk.Label(frame, text="Power Factor:").grid(row=3, column=0, sticky="w", pady=8)
pf_var = tk.DoubleVar(value=0.85)
ttk.Entry(frame, textvariable=pf_var, width=30).grid(row=3, column=1, pady=8)

ttk.Label(frame, text="Conductor Type:").grid(row=4, column=0, sticky="w", pady=8)
conductor_var = tk.StringVar(value="Rabbit")
cond_combo = ttk.Combobox(frame, textvariable=conductor_var, values=["Weasel", "Rabbit", "Raccoon", "Dog"], state="readonly")
cond_combo.grid(row=4, column=1, pady=8)

ttk.Button(frame, text="Calculate Voltage Drop", command=calculate_vd).grid(row=5, column=0, columnspan=2, pady=20)

# Result
result_text = tk.StringVar()
status_text = tk.StringVar(value="Enter values and click Calculate")

tk.Label(root, textvariable=result_text, font=("Arial", 18, "bold"), bg="#0f172a", fg="white").pack(pady=10)
status_label = tk.Label(root, textvariable=status_text, font=("Arial", 14), bg="#0f172a")
status_label.pack(pady=5)

# Graph
fig, ax = plt.subplots(figsize=(8, 4))
canvas = FigureCanvasTkAgg(fig, root)
canvas.get_tk_widget().pack(pady=10, fill="x", padx=30)

# Rough Sketch
sketch = tk.Label(root, text="""Substation ────────────────────► Consumer End
          {} Conductor   ({} km)""".format("Rabbit", 5.0), 
          font=("Courier", 11), bg="#1e2937", fg="#94a3b8", justify="left")
sketch.pack(pady=15, fill="x", padx=40)

# Footer
footer_frame = tk.Frame(root, bg="#0f172a")
footer_frame.pack(side="bottom", fill="x", pady=20)

tk.Label(footer_frame, text="Made with ❤️ by @iamanujnarang", 
         font=("Arial", 14), bg="#0f172a", fg="#facc15").pack()

tk.Label(footer_frame, text="Facebook | Instagram | X | LinkedIn   →   iamanujnarang", 
         font=("Arial", 10), bg="#0f172a", fg="#94a3b8").pack(pady=5)

tk.Label(footer_frame, text="Powered by Beeclue Tech", fg="#60a5fa", 
         bg="#0f172a", cursor="hand2").pack()
tk.Label(footer_frame, text="https://beeclue.com/", fg="#60a5fa", 
         bg="#0f172a").pack()

root.mainloop()
