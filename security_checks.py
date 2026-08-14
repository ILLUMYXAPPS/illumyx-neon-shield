import os
import platform
import shutil
import socket
import subprocess
from dataclasses import dataclass
from typing import List


@dataclass
class CheckResult:
    name: str
    result: str
    state: str
    detail: str = ""


def _run(command, timeout=4):
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        output = (completed.stdout or completed.stderr or "").strip()
        return completed.returncode, output
    except (OSError, subprocess.SubprocessError):
        return None, ""


def _disk_check() -> CheckResult:
    total, _, free = shutil.disk_usage(os.path.expanduser("~"))
    pct = (free / total) * 100 if total else 0
    state = "ok" if pct >= 15 else "warn"
    detail = "Healthy free-space margin." if state == "ok" else "Low free space can interfere with updates, logs, and recovery operations."
    return CheckResult("Disk free", f"{pct:.1f}%", state, detail)


def _firewall_check() -> CheckResult:
    system = platform.system()

    if system == "Windows":
        code, output = _run([
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-NetFirewallProfile | Where-Object {$_.Enabled -eq $true}).Count",
        ])
        if code == 0 and output:
            try:
                enabled = int(output.splitlines()[-1])
                if enabled > 0:
                    return CheckResult("Firewall", "Enabled", "ok", f"{enabled} Windows firewall profile(s) enabled.")
            except ValueError:
                pass
        return CheckResult("Firewall", "Unknown", "info", "Windows firewall status could not be read without changing the system.")

    if system == "Darwin":
        tool = "/usr/libexec/ApplicationFirewall/socketfilterfw"
        if os.path.exists(tool):
            code, output = _run([tool, "--getglobalstate"])
            if code == 0 and output:
                if "enabled" in output.lower():
                    return CheckResult("Firewall", "Enabled", "ok", output)
                if "disabled" in output.lower():
                    return CheckResult("Firewall", "Disabled", "warn", "macOS application firewall appears disabled.")
        return CheckResult("Firewall", "Unknown", "info", "macOS firewall status was unavailable.")

    if system == "Linux":
        if shutil.which("ufw"):
            code, output = _run(["ufw", "status"])
            if code == 0 and output:
                if "status: active" in output.lower():
                    return CheckResult("Firewall", "Active", "ok", "UFW reports an active firewall.")
                if "status: inactive" in output.lower():
                    return CheckResult("Firewall", "Inactive", "warn", "UFW reports the firewall is inactive.")
        if shutil.which("firewall-cmd"):
            code, output = _run(["firewall-cmd", "--state"])
            if code == 0 and "running" in output.lower():
                return CheckResult("Firewall", "Active", "ok", "firewalld is running.")
        return CheckResult("Firewall", "Unknown", "info", "No supported firewall status command was available.")

    return CheckResult("Firewall", "Unsupported OS", "info", "Firewall reporting is not implemented for this platform yet.")


def _defender_check() -> CheckResult:
    if platform.system() != "Windows":
        return CheckResult("Built-in protection", "Platform specific", "info", "Windows Defender status is checked only on Windows.")

    code, output = _run([
        "powershell",
        "-NoProfile",
        "-Command",
        "$s=Get-MpComputerStatus; Write-Output ($s.AntivirusEnabled.ToString()+','+$s.RealTimeProtectionEnabled.ToString())",
    ])
    if code == 0 and output:
        parts = output.splitlines()[-1].lower().split(",")
        if len(parts) == 2 and parts[0] == "true" and parts[1] == "true":
            return CheckResult("Built-in protection", "Active", "ok", "Microsoft Defender antivirus and real-time protection report enabled.")
        return CheckResult("Built-in protection", "Needs review", "warn", "Microsoft Defender did not report both antivirus and real-time protection enabled.")

    return CheckResult("Built-in protection", "Unknown", "info", "Defender status could not be read.")


def run_local_checks() -> List[CheckResult]:
    hostname = socket.gethostname() or "Unavailable"
    results = [
        CheckResult("Device", platform.node() or hostname or "Unknown", "info", "Local device name."),
        CheckResult("Operating system", f"{platform.system()} {platform.release()}", "info", platform.platform()),
        CheckResult("Python", platform.python_version(), "info", "Runtime used by Neon Shield."),
        _disk_check(),
        _firewall_check(),
        _defender_check(),
        CheckResult("Local hostname", hostname, "info", "Shown locally only; Neon Shield does not transmit this value."),
    ]
    return results
