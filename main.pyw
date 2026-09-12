import sys
import subprocess
from tkinter import messagebox as mbox

try:
    subprocess.run([sys.executable, "-m", "src"], check=True)
except Exception:
    mbox.showerror("Project Manager", "A critical error occured. Check logs!")
