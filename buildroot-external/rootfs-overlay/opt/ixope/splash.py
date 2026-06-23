#!/usr/bin/env python3
"""Boot splash screen — shows IXOPE logo centered on 480x480 display"""
import tkinter as tk
import sys

def show_splash():
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.configure(bg='black')
    root.overrideredirect(True)

    # Big centered IXOPE text
    title = tk.Label(root, text="IXOPE", font=("Helvetica", 72, "bold"),
                     fg="white", bg="black")
    title.place(relx=0.5, rely=0.4, anchor="center")

    # Loading text below
    loading = tk.Label(root, text="Loading...", font=("Helvetica", 24),
                       fg="gray", bg="black")
    loading.place(relx=0.5, rely=0.6, anchor="center")

    # Auto-close after 10 seconds (app will kill us sooner)
    root.after(10000, root.destroy)
    root.update()
    root.mainloop()

if __name__ == "__main__":
    try:
        show_splash()
    except Exception:
        pass
