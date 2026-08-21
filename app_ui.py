import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from security_checks import CheckResult, run_local_checks
from copyright_scanner import fingerprint_reference, render_transcript, scan_targets

APP_NAME = "ILLUMYX NEON SHIELD v2"
APP_VERSION = "v2.1-beta"
BG = "#050814"
SIDEBAR = "#091127"
PANEL = "#0d1733"
PANEL_ALT = "#132149"
TEXT = "#f7fbff"
MUTED = "#8fa3c9"
CYAN = "#2cecff"
MAGENTA = "#ff3bd4"
VIOLET = "#8e5cff"
NEON = "#37f2b5"
WARN = "#ffca62"
DANGER = "#ff6b8a"


class NeonShield(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1180x780")
        self.minsize(980, 680)
        self.configure(bg=BG)
        self.last_results = []
        self.last_copyright_matches = []
        self._build()
        self.refresh()

    def _build(self):
        root = tk.Frame(self, bg=BG)
        root.pack(fill="both", expand=True)

        sidebar = tk.Frame(root, bg=SIDEBAR, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand = tk.Frame(sidebar, bg=SIDEBAR)
        brand.pack(fill="x", padx=20, pady=(24, 16))
        tk.Label(brand, text="◈ ILLUMYX", bg=SIDEBAR, fg=CYAN,
                 font=("Arial", 18, "bold")).pack(anchor="w")
        tk.Label(brand, text="NEON SHIELD", bg=SIDEBAR, fg=MAGENTA,
                 font=("Arial", 13, "bold")).pack(anchor="w", pady=(2, 0))
        tk.Label(brand, text=APP_VERSION, bg=SIDEBAR, fg=MUTED,
                 font=("Arial", 9)).pack(anchor="w", pady=(4, 0))

        self._nav_item(sidebar, "▣  Dashboard", active=True)
        self._nav_item(sidebar, "⌁  Local checks")
        self._nav_item(sidebar, "◉  Copyright scanner")
        self._nav_item(sidebar, "⇩  Reports")
        self._nav_item(sidebar, "ⓘ  About")

        safe = tk.Frame(sidebar, bg=PANEL, padx=14, pady=14)
        safe.pack(side="bottom", fill="x", padx=14, pady=16)
        tk.Label(safe, text="LOCAL-FIRST", bg=PANEL, fg=NEON,
                 font=("Arial", 9, "bold")).pack(anchor="w")
        tk.Label(safe, text="Read-only checks\nNo remote scanning\nNo credential collection",
                 bg=PANEL, fg=MUTED, justify="left", font=("Arial", 9)).pack(anchor="w", pady=(5, 0))

        main = tk.Frame(root, bg=BG)
        main.pack(side="left", fill="both", expand=True)

        header = tk.Frame(main, bg=BG)
        header.pack(fill="x", padx=26, pady=(22, 8))
        left_header = tk.Frame(header, bg=BG)
        left_header.pack(side="left", fill="x", expand=True)
        tk.Label(left_header, text="SYSTEM STATUS", bg=BG, fg=TEXT,
                 font=("Arial", 22, "bold")).pack(anchor="w")
        tk.Label(left_header,
                 text="Verified local posture checks and copyright evidence scanning",
                 bg=BG, fg=MUTED, font=("Arial", 10)).pack(anchor="w", pady=(4, 0))
        self.timestamp = tk.Label(header, text="", bg=BG, fg=MUTED, font=("Arial", 9))
        self.timestamp.pack(side="right", anchor="n", pady=4)

        hero = tk.Frame(main, bg=PANEL, padx=20, pady=18)
        hero.pack(fill="x", padx=26, pady=(4, 12))
        hero_left = tk.Frame(hero, bg=PANEL)
        hero_left.pack(side="left", fill="x", expand=True)
        tk.Label(hero_left, text="✦ NEON SHIELD", bg=PANEL, fg=CYAN,
                 font=("Arial", 11, "bold")).pack(anchor="w")
        self.hero_status = tk.Label(hero_left, text="CHECKING", bg=PANEL, fg=NEON,
                                    font=("Arial", 24, "bold"))
        self.hero_status.pack(anchor="w", pady=(6, 2))
        self.hero_detail = tk.Label(hero_left,
                                    text="Running local, read-only checks...",
                                    bg=PANEL, fg=MUTED, font=("Arial", 10))
        self.hero_detail.pack(anchor="w")
        tk.Label(hero, text="◈", bg=PANEL, fg=VIOLET,
                 font=("Arial", 42, "bold")).pack(side="right", padx=12)

        summary = tk.Frame(main, bg=BG)
        summary.pack(fill="x", padx=26, pady=(0, 12))
        self.summary_ok = self._summary_card(summary, "OK", "0", NEON)
        self.summary_review = self._summary_card(summary, "REVIEW", "0", WARN)
        self.summary_info = self._summary_card(summary, "INFO", "0", CYAN)

        body = tk.Frame(main, bg=BG)
        body.pack(fill="both", expand=True, padx=26, pady=(0, 10))

        table_frame = tk.Frame(body, bg=PANEL, padx=1, pady=1)
        table_frame.pack(fill="both", expand=True)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                        foreground=TEXT, rowheight=38, borderwidth=0, font=("Arial", 9))
        style.configure("Treeview.Heading", background=PANEL_ALT, foreground=CYAN,
                        relief="flat", font=("Arial", 9, "bold"))
        style.map("Treeview", background=[("selected", "#18305f")], foreground=[("selected", TEXT)])

        self.table = ttk.Treeview(
            table_frame,
            columns=("check", "result", "state", "detail"),
            show="headings",
        )
        self.table.heading("check", text="LOCAL CHECK")
        self.table.heading("result", text="RESULT")
        self.table.heading("state", text="STATE")
        self.table.heading("detail", text="DETAIL")
        self.table.column("check", width=160)
        self.table.column("result", width=180)
        self.table.column("state", width=90, anchor="center")
        self.table.column("detail", width=480)
        self.table.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self._show_selected_recommendation)

        recommendation_frame = tk.Frame(main, bg=PANEL, padx=16, pady=12)
        recommendation_frame.pack(fill="x", padx=26, pady=(0, 10))
        tk.Label(recommendation_frame, text="GUIDED RECOMMENDATION", bg=PANEL, fg=MAGENTA,
                 font=("Arial", 9, "bold")).pack(anchor="w")
        self.recommendation = tk.Label(
            recommendation_frame,
            text="Select a result to see a recommended next step.",
            bg=PANEL,
            fg=TEXT,
            font=("Arial", 10),
            justify="left",
            wraplength=880,
        )
        self.recommendation.pack(anchor="w", pady=(5, 0))

        copyright_frame = tk.Frame(main, bg=PANEL_ALT, padx=14, pady=12)
        copyright_frame.pack(fill="x", padx=26, pady=(0, 10))
        tk.Label(copyright_frame, text="◉ COPYRIGHT EVIDENCE SCANNER", bg=PANEL_ALT,
                 fg=CYAN, font=("Arial", 9, "bold")).pack(side="left")
        tk.Label(copyright_frame,
                 text="Fingerprint your masters, scan a target folder, and export a match transcript.",
                 bg=PANEL_ALT, fg=MUTED, font=("Arial", 9)).pack(side="left", padx=(12, 0))
        self._button(copyright_frame, "⌕  Scan files", self.run_copyright_scan, VIOLET, TEXT).pack(side="right")

        footer = tk.Frame(main, bg=BG)
        footer.pack(fill="x", padx=26, pady=(0, 22))
        self._button(footer, "↻  Refresh checks", self.refresh, CYAN, "#02121a").pack(side="left")
        self._button(footer, "⇩  Export report", self.export_report, PANEL_ALT, TEXT).pack(side="left", padx=(10, 0))
        tk.Label(footer, text="Secure. Smart. Neon.", bg=BG, fg=VIOLET,
                 font=("Arial", 10, "bold")).pack(side="right")

    def _nav_item(self, parent, text, active=False):
        bg = PANEL_ALT if active else SIDEBAR
        fg = CYAN if active else MUTED
        tk.Label(parent, text=text, bg=bg, fg=fg, anchor="w",
                 padx=16, pady=10, font=("Arial", 10, "bold" if active else "normal")).pack(fill="x", padx=12, pady=2)

    def _button(self, parent, text, command, bg, fg):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                         activebackground=VIOLET, activeforeground=TEXT,
                         relief="flat", padx=16, pady=10, font=("Arial", 10, "bold"))

    def _summary_card(self, parent, label, value, accent):
        card = tk.Frame(parent, bg=PANEL, padx=16, pady=12)
        card.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(card, text=label, bg=PANEL, fg=MUTED,
                 font=("Arial", 9, "bold")).pack(anchor="w")
        value_label = tk.Label(card, text=value, bg=PANEL, fg=accent,
                               font=("Arial", 18, "bold"))
        value_label.pack(anchor="w", pady=(4, 0))
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
            overall = "REVIEW RECOMMENDED"
            overall_colour = WARN
            hero_detail = "One or more local settings may need your attention."
        elif not results:
            overall = "NO RESULTS"
            overall_colour = MUTED
            hero_detail = "No local check results were returned."
        else:
            overall = "CHECKS COMPLETE"
            overall_colour = NEON
            hero_detail = "No REVIEW items were reported by the checks Neon Shield can verify."

        self.hero_status.config(text=overall, fg=overall_colour)
        self.hero_detail.config(text=hero_detail)
        self.summary_ok.config(text=str(counts["ok"]))
        self.summary_review.config(text=str(counts["warn"]))
        self.summary_info.config(text=str(counts["info"]))
        self.timestamp.config(text=f"Last refresh  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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

    def run_copyright_scan(self):
        reference_dir = filedialog.askdirectory(title="Select your ILLUMYX master/reference folder")
        if not reference_dir:
            return
        target_dir = filedialog.askdirectory(title="Select the folder to scan for matching files")
        if not target_dir:
            return

        self.hero_status.config(text="SCANNING COPYRIGHT FILES", fg=CYAN)
        self.hero_detail.config(text="Fingerprinting reference files and comparing the target tree locally...")
        self.update_idletasks()

        try:
            references = fingerprint_reference(Path(reference_dir))
            matches = scan_targets(references, Path(target_dir))
            self.last_copyright_matches = list(matches)
            transcript = render_transcript(matches, len(references), Path(target_dir))
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Copyright scan failed safely: {type(exc).__name__}: {exc}")
            return

        self.hero_status.config(
            text="MATCHES FOUND" if matches else "NO MATCHES FOUND",
            fg=WARN if matches else NEON,
        )
        self.hero_detail.config(
            text=f"Fingerprint registry: {len(references)} files | Candidate matches: {len(matches)}"
        )
        self.recommendation.config(
            text=(
                "Candidate matches detected. Export the transcript and verify each item before making a copyright claim."
                if matches else
                "No candidate matches were detected with the current local fingerprint rules."
            )
        )

        if matches:
            summary = "\n\n".join(
                f"#{i + 1}  {m.match_type}  {m.confidence:.1f}%\nSource: {m.source}\nCandidate: {m.candidate}\n{m.detail}"
                for i, m in enumerate(matches[:20])
            )
            messagebox.showwarning(APP_NAME, f"{len(matches)} candidate match(es) found.\n\n{summary}")
        else:
            messagebox.showinfo(APP_NAME, "No candidate matches were detected.")

        path = filedialog.asksaveasfilename(
            title="Save copyright match transcript",
            defaultextension=".txt",
            initialfile=f"illumyx-copyright-match-transcript-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt",
            filetypes=[("Text transcript", "*.txt"), ("All files", "*.*")],
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as report:
                    report.write(transcript)
                messagebox.showinfo(APP_NAME, "Copyright match transcript exported successfully.")
            except OSError as exc:
                messagebox.showerror(APP_NAME, f"The transcript could not be saved: {exc}")

    def export_report(self):
        if not self.last_results and not self.last_copyright_matches:
            messagebox.showinfo(APP_NAME, "There are no check results or copyright matches to export yet.")
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
            f"Version: {APP_VERSION}",
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            "Scope: local, read-only device posture checks and local copyright evidence scanning",
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

        if self.last_copyright_matches:
            lines.extend([
                "COPYRIGHT MATCHES",
                "Candidate matches require verification before any copyright claim.",
                "",
            ])
            for index, match in enumerate(self.last_copyright_matches, 1):
                lines.extend([
                    f"MATCH #{index} | {match.match_type} | CONFIDENCE {match.confidence:.1f}%",
                    f"Source: {match.source}",
                    f"Candidate: {match.candidate}",
                    f"Source SHA-256: {match.source_sha256}",
                    f"Candidate SHA-256: {match.candidate_sha256}",
                    f"Detail: {match.detail}",
                    f"Detected: {match.detected_at}",
                    "Status: CANDIDATE MATCH - VERIFY BEFORE MAKING ANY COPYRIGHT CLAIM",
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
