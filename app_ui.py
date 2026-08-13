import os
import platform
import shutil
import socket
import tkinter as tk
from datetime import datetime
from tkinter import ttk

APP_NAME = "ILLUMYX NEON SHIELD v2"
BG = "#080b16"
PANEL = "#11172a"
TEXT = "#f4f7ff"
MUTED = "#9aa7c2"
NEON = "#33f5c5"
WARN = "#ffcc66"


def local_checks():
    """Return non-invasive, local device health information only."""
    total, used, free = shutil.disk_usage(os.path.expanduser("~"))
    free_pct = (free / total) * 100 if total else 0
    hostname = socket.gethostname()
    return [
        ("Device", platform.node() or hostname or "Unknown", "info"),
        ("Operating system", f"{platform.system()} {platform.release()}", "info"),
        ("Python", platform.python_version(), "info"),
        ("Disk free", f"{free_pct:.1f}%", "ok" if free_pct >= 15 else "warn"),
        ("Local hostname", hostname or "Unavailable", "info"),
    ]


class NeonShield(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("820x600")
        self.minsize(700, 520)
        self.configure(bg=BG)
        self._build()
        self.refresh()

    def _build(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=28, pady=(26, 12))
        tk.Label(header, text="🛡  ILLUMYX", bg=BG, fg=NEON,
                 font=("Arial", 24, "bold")).pack(anchor="w")
        tk.Label(header, text="NEON SHIELD v2  •  Local Security Dashboard",
                 bg=BG, fg=TEXT, font=("Arial", 13, "bold")).pack(anchor="w", pady=(4, 0))
        tk.Label(header,
                 text="A transparent defensive dashboard for your own device. It reports local status and does not claim to block every threat.",
                 bg=BG, fg=MUTED, font=("Arial", 10), wraplength=740,
                 justify="left").pack(anchor="w", pady=(8, 0))

        status = tk.Frame(self, bg=PANEL, padx=20, pady=18)
        status.pack(fill="x", padx=28, pady=10)
        self.status_title = tk.Label(status, text="STATUS: CHECKING", bg=PANEL,
                                     fg=NEON, font=("Arial", 16, "bold"))
        self.status_title.pack(anchor="w")
        self.timestamp = tk.Label(status, text="", bg=PANEL, fg=MUTED, font=("Arial", 9))
        self.timestamp.pack(anchor="w", pady=(5, 0))

        table_frame = tk.Frame(self, bg=BG)
        table_frame.pack(fill="both", expand=True, padx=28, pady=8)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                        foreground=TEXT, rowheight=34, borderwidth=0)
        style.configure("Treeview.Heading", background="#171f38", foreground=TEXT,
                        relief="flat", font=("Arial", 10, "bold"))
        self.table = ttk.Treeview(table_frame, columns=("check", "result", "state"), show="headings")
        self.table.heading("check", text="LOCAL CHECK")
        self.table.heading("result", text="RESULT")
        self.table.heading("state", text="STATE")
        self.table.column("check", width=180)
        self.table.column("result", width=390)
        self.table.column("state", width=100, anchor="center")
        self.table.pack(fill="both", expand=True)

        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=28, pady=(8, 24))
        tk.Button(footer, text="↻  Refresh local checks", command=self.refresh,
                  bg=NEON, fg="#04110d", activebackground="#75ffe1",
                  relief="flat", padx=16, pady=9, font=("Arial", 10, "bold")).pack(side="left")
        tk.Label(footer, text="No remote scanning • No credential collection • No attack tools",
                 bg=BG, fg=MUTED, font=("Arial", 9)).pack(side="right")

    def refresh(self):
        for row in self.table.get_children():
            self.table.delete(row)
        checks = local_checks()
        warning = False
        for name, value, state in checks:
            if state == "warn":
                warning = True
            label = "ACTION" if state == "warn" else ("OK" if state == "ok" else "INFO")
            self.table.insert("", "end", values=(name, value, label))
        self.status_title.config(
            text="STATUS: ACTION RECOMMENDED" if warning else "STATUS: LOCAL CHECKS COMPLETE",
            fg=WARN if warning else NEON,
        )
        self.timestamp.config(text=f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    NeonShield().mainloop()
