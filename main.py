"""
Accessible Campus Navigator
============================
A desktop application that helps students find accessible routes
between locations on a fictional college campus.

Main entry point for the application.
"""

import tkinter as tk
from tkinter import ttk
import sys


def main():
    """Launch the Accessible Campus Navigator application."""
    root = tk.Tk()
    root.title("Accessible Campus Navigator")
    root.geometry("1000x700")
    root.minsize(800, 600)

    # Center the window on screen
    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - 1000) // 2
    y = (screen_height - 700) // 2
    root.geometry(f"1000x700+{x}+{y}")

    # ── Startup splash frame ──────────────────────────────────────────
    frame = ttk.Frame(root, padding=40)
    frame.place(relx=0.5, rely=0.5, anchor="center")

    title_label = ttk.Label(
        frame,
        text="♿  Accessible Campus Navigator",
        font=("Segoe UI", 24, "bold"),
    )
    title_label.pack(pady=(0, 10))

    subtitle_label = ttk.Label(
        frame,
        text="Helping every student navigate the campus with ease",
        font=("Segoe UI", 12),
        foreground="#555555",
    )
    subtitle_label.pack(pady=(0, 20))

    version_label = ttk.Label(
        frame,
        text="Version 1.0  •  Phase 1 – Foundation",
        font=("Segoe UI", 9),
        foreground="#999999",
    )
    version_label.pack()

    status_label = ttk.Label(
        frame,
        text="Application skeleton loaded successfully.",
        font=("Segoe UI", 10),
        foreground="#2a7f2a",
    )
    status_label.pack(pady=(20, 0))

    root.mainloop()


if __name__ == "__main__":
    main()
