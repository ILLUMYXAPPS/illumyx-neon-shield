import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from security_checks import CheckResult, run_local_checks

APP_NAME = "ILLUMYX NEON SHIELD v2"
BG = "#080b16"
PANEL = "#11172a"
PANEL_ALT = "#171f38"
TEXT = "#f4f7ff"
MUTED = "#9aa7c2"
NEON = "#33f5c5"
WARN = "#ffcc66"


class NeonShield(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1040x760")
        self.minsize(860, 620)
        self.configure(bg=BG)
        self.last_results = []
        self._build()
        self.refresh()

    def _build(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=28, pady=(24, 12))

        tk.Label(header, text="🛡  ILLUMYX NEON SHIELD", bg=BG, fg=NEON,
                 font=("Arial", 25, "bold")).pack(anchor="w")
        tk.Label(header, text="v2 • Local Security Posture Dashboard", bg=BG, fg=TEXT,
                 font=("Arial", 13, "bold")).pack(anchor="w", pady=(4, 0))
        tk.Label(
            header,
            text=(
                "Defensive, local-only checks for your own device. Neon Shield reports what it can verify, "
                "labels unknowns clearly, and does not claim to guarantee protection."
            ),
            bg=BG,
            fg=MUTED,
            font=("Arial", 10),
            wraplength=940,
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
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                        foreground=TEXT, rowheight=36, borderwidth=0)
        style.configure("Treeview.Heading", background=PANEL_ALT, foreground=TEXT,
                        relief="flat", font=("Arial", 10, "bold"))
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
        self.table.column("detail", width=470)
        self.table.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self._show_selected_recommendation)

        recommendation_frame = tk.Frame(self, bg=PANEL, padx=16, pady=12)
        recommendation_frame.pack(fill="x", padx=28, pady=(4, 8))
        tk.Label(recommendation_frame, text="GUIDED RECOMMENDATION", bg=PANEL, fg=MUTED,
                 font=("Arial", 9, "bold")).pack(anchor="w")
        self.recommendation = tk.Label(
            recommendation_frame,
            text="Select a result to see a recommended next step.",
            bg=PANEL,
            fg=TEXT,
            font=("Arial", 10),
            justify="left",
            wraplength=950,
        )
        self.recommendation.pack(anchor="w", pady=(5, 0))

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
        tk.Button(
            footer,
            text="⇩  Export report",
            command=self.export_report,
            bg=PANEL_ALT,
            fg=TEXT,
            activebackground="#22304f",
            activeforeground=TEXT,
            relief="flat",
            padx=16,
            pady=9,
            font=("Arial", 10, "bold"),
        ).pack(side="left", padx=(10, 0))
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
        tk.Label(card, text=label, bg=PANEL, fg=MUTED,
                 font=("Arial", 9, "bold")).pack(anchor="w")
        value_label = tk.Label(card, text=value, bg=PANEL, fg=accent,
                               font=("Arial", 15, "bold"))
        value_label.pack(anchor="w", pady=(3, 0))
        return value_label

    def refresh(self):
        for row in self.table.get_children():
            self.table.delete(row)

        try:
            results = run_local_checks()
        except Exception as exc:
            results = [
                CheckResult(
                    "Neon Shield",
                    "Check engine unavailable",
                    "info",
                    f"Refresh failed safely: {type(exc).__name__}.",
                )
            ]

        self.last_results = list(results)
        counts = {"ok": 0, "warn": 0, "info": 0}
        for index, item in enumerate(results):
            state = item.state if item.state in counts else "info"
            counts[state] += 1
            state_label = {"ok": "OK", "warn": "REVIEW", "info": "INFO"}[state]
            self.table.insert(
                "",
                "end",
                iid=str(index),
                values=(item.name, item.result, state_label, item.detail),
            )

        if counts["warn"]:
            overall = "ACTION RECOMMENDED"
            overall_colour = WARN
        elif not results:
            overall = "NO CHECK RESULTS"
            overall_colour = MUTED
        else:
            overall = "CHECKS COMPLETE"
            overall_colour = NEON

        self.summary_status.config(text=overall, fg=overall_colour)
        self.summary_ok.config(text=str(counts["ok"]))
        self.summary_review.config(text=str(counts["warn"]))
        self.summary_info.config(text=str(counts["info"]))
        self.timestamp.config(text=f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.recommendation.config(text=self._overall_recommendation(results))

    def _show_selected_recommendation(self, _event=None):
        selection = self.table.selection()
        if not selection:
            return
        try:
            item = self.last_results[int(selection[0])]
        except (ValueError, IndexError):
            return
        self.recommendation.config(text=self._recommendation_for(item))

    @staticmethod
    def _recommendation_for(item):
        if item.state == "ok":
            return f"{item.name}: No action needed right now. Keep normal updates and maintenance current."
        if item.name == "Disk free" and item.state == "warn":
            return "Disk free: Free some storage space before major updates or backups. Aim for at least 15% free space."
        if item.name == "Firewall" and item.state == "warn":
            return "Firewall: Review your operating system firewall settings and enable the appropriate firewall profile if it was intentionally disabled."
        if item.name == "Built-in protection" and item.state == "warn":
            return "Built-in protection: Open your operating system security settings and verify antivirus and real-time protection are enabled."
        if item.state == "warn":
            return f"{item.name}: Review this item in your operating system settings. Neon Shield will not change the setting automatically."
        return f"{item.name}: Neon Shield could not make a security judgement from this information. This is informational only."

    def _overall_recommendation(self, results):
        review_items = [item for item in results if item.state == "warn"]
        if not review_items:
            return "No REVIEW items were reported. Select any row for more context about that result."
        names = ", ".join(item.name for item in review_items)
        return f"Review recommended for: {names}. Select a REVIEW row to see the suggested next step."

    def export_report(self):
        if not self.last_results:
            messagebox.showinfo(APP_NAME, "There are no check results to export yet.")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = filedialog.asksaveasfilename(
            title="Export Neon Shield report",
            defaultextension=".txt",
            initialfile=f"neon-shield-report-{timestamp}.txt",
            filetypes=[("Text report", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return

        lines = [
            APP_NAME,
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            "Scope: local, read-only device posture checks",
            "",
        ]
        for item in self.last_results:
            state_label = {"ok": "OK", "warn": "REVIEW", "info": "INFO"}.get(item.state, "INFO")
            lines.extend([
                f"[{state_label}] {item.name}: {item.result}",
                f"Detail: {item.detail}",
                f"Recommendation: {self._recommendation_for(item)}",
                "",
            ])

        try:
            with open(path, "w", encoding="utf-8") as report:
                report.write("\n".join(lines))
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"The report could not be saved: {exc}")
            return

        messagebox.showinfo(APP_NAME, "Neon Shield report exported successfully.")


if __name__ == "__main__":
    NeonShield().mainloop()
