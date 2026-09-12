import sys
import subprocess
from tkinter import messagebox

try:
    subprocess.run([sys.executable, "./src/main.py"], check=True)
except Exception:
    messagebox.showerror("Project Manager", "A critical error occured, check logs!")
