import tkinter as tk

try:
    root = tk.Tk()
    label = tk.Label(root, text="Tkinter is working")
    label.pack()
    print("Tkinter initialized successfully")
    root.update()
    root.destroy()
except Exception as e:
    print(f"Tkinter failed: {e}")
