import tkinter as tk
from datetime import datetime
from tkinter import ttk

from security_checks import run_local_checks

APP_NAME = "ILLUMYX NEON SHIELD v2"
BG = "#080b16"
PANEL = "#11172a"
PANEL_ALT = "#171f38"
TEXT = "#f4f7ff"
MUTED = "#9aa7c2"
NEON = "#33f5c5"
WARN = "#ffcc66"
DANGER = "#ff6b7a"


class NeonShield(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("980x700")
        self.minsize(820, 600)
        self.configure(bg=BG)
        self._build()
        self.refresh()

    def _build(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=28, pady=(24, 12))

        tk.Label(
            header,
            text="🛡  ILLUMYX NEON SHIELD",
            bg=BG,
            fg=NEON,
            font=("Arial", 25, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="v2 • Local Security Posture Dashboard",
            bg=BG,
            fg=TEXT,
            font=("Arial", 13, "bold"),
        ).pack(anchor="w", pady=(4, 0))
        tk.Label(
            header,
            text=(
                "Defensive, local-only checks for your own device. Neon Shield reports what it can verify, "
                "labels unknowns clearly, and does not claim to guarantee protection."
            ),
            bg=BG,
            fg=MUTED,
            font=("Arial", 10),
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        summary = tk.Frame(self, bg=BG)
        summary.pack(fill="x", padx=28, pady=(4, 10))

        self.summary_status = self._summary_card(summary, "OVERALL", "CHECKING", NEON)
        self.summary_ok = self._summary_card(summary, "OK", "0", NEON)
        self.summary_review = self._summary_card(summary, "REVIEW", "0", WARN)
        self.summary_info = self._summary_card(summary, "INFO", "0", MUTED)

        table_frame = tk.Frame(self, bg=BG)
        table_frame.pack(fill="both", expand=True, padx=28, pady=8)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=PANEL,
            fieldbackground=PANEL,
            foreground=TEXT,
            rowheight=36,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=PANEL_ALT,
            foreground=TEXT,
            relief="flat",
            font=("Arial", 10, "bold"),
        )
        style.map("Treeview", background=[("selected", "#22304f")])

        self.table = ttk.Treeview(
            table_frame,
            columns=("check", "result", "state", "detail"),
            show="headings",
        )
        self.table.heading("check", text="LOCAL CHECK")
        self.table.heading("result", text="RESULT")
        self.table.heading("state", text="STATE")
        self.table.heading("detail", text="DETAIL")
        self.table.column("check", width=165)
        self.table.column("result", width=210)
        self.table.column("state", width=95, anchor="center")
        self.table.column("detail", width=430)
        self.table.pack(fill="both", expand=True)

        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=28, pady=(8, 22))

        tk.Button(
            footer,
            text="↻  Refresh checks",
            command=self.refresh,
            bg=NEON,
            fg="#04110d",
            activebackground="#75ffe1",
            relief="flat",
            padx=16,
            pady=9,
            font=("Arial", 10, "bold"),
        ).pack(side="left")

        self.timestamp = tk.Label(footer, text="", bg=BG, fg=MUTED, font=("Arial", 9))
        self.timestamp.pack(side="left", padx=14)

        tk.Label(
            footer,
            text="Local checks only • No credential collection • No remote scanning",
            bg=BG,
            fg=MUTED,
            font=("Arial", 9),
        ).pack(side="right")

    def _summary_card(self, parent, label, value, accent):
        card = tk.Frame(parent, bg=PANEL, padx=16, pady=12)
        card.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(card, text=label, bg=PANEL, fg=MUTED, font=("Arial", 9, "bold")).pack(anchor="w")
        value_label = tk.Label(card, text=value, bg=PANEL, fg=accent, font=("Arial", 15, "bold"))
        value_label.pack(anchor="w", pady=(3, 0))
        return value_label

    def refresh(self):
        for row in self.table.get_children():
            self.table.delete(row)

        results = run_local_checks()
        counts = {"ok": 0, "warn": 0, "info": 0}

        for item in results:
            counts[item.state] = counts.get(item.state, 0) + 1
            state_label = {
                "ok": "OK",
                "warn": "REVIEW",
                "info": "INFO",
            }.get(item.state, item.state.upper())
            self.table.insert(
                "",
                "end",
                values=(item.name, item.result, state_label, item.detail),
            )

        if counts.get("warn", 0):
            overall = "ACTION RECOMMENDED"
            overall_colour = WARN
        else:
            overall = "CHECKS COMPLETE"
            overall_colour = NEON

        self.summary_status.config(text=overall, fg=overall_colour)
        self.summary_ok.config(text=str(counts.get("ok", 0)))
        self.summary_review.config(text=str(counts.get("warn", 0)))
        self.summary_info.config(text=str(counts.get("info", 0)))
        self.timestamp.config(text=f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    NeonShield().mainloop()
