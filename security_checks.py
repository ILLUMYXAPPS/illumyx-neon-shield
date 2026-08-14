import os
import platform
import shutil
import socket
import subprocess
from dataclasses import dataclass
from typing import Callable, List


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
            encoding="utf-8",
            errors="replace",
        )
        output = (completed.stdout or completed.stderr or "").strip()
        return completed.returncode, output
    except (OSError, subprocess.SubprocessError, ValueError):
        return None, ""


def _safe_check(name: str, check: Callable[[], CheckResult]) -> CheckResult:
    try:
        return check()
    except Exception as exc:
        return CheckResult(name, "Unknown", "info", f"Check unavailable: {type(exc).__name__}.")


def _disk_check() -> CheckResult:
    total, _, free = shutil.disk_usage(os.path.expanduser("~"))
    pct = (free / total) * 100 if total else 0
    state = "ok" if pct >= 15 else "warn"
    detail = (
        "Healthy free-space margin."
        if state == "ok"
        else "Low free space can interfere with updates, logs, and recovery operations."
    )
    return CheckResult("Disk free", f"{pct:.1f}%", state, detail)


def _powershell_command():
    return shutil.which("powershell") or shutil.which("powershell.exe") or shutil.which("pwsh")


def _firewall_check() -> CheckResult:
    system = platform.system()

    if system == "Windows":
        powershell = _powershell_command()
        if not powershell:
            return CheckResult("Firewall", "Unknown", "info", "PowerShell was not available to read firewall status.")
        code, output = _run([
            powershell,
            "-NoProfile",
            "-Command",
            "(Get-NetFirewallProfile | Where-Object {$_.Enabled -eq $true}).Count",
        ])
        if code == 0 and output:
            try:
                enabled = int(output.splitlines()[-1].strip())
                if enabled > 0:
                    return CheckResult("Firewall", "Enabled", "ok", f"{enabled} Windows firewall profile(s) enabled.")
                return CheckResult("Firewall", "Disabled", "warn", "No enabled Windows firewall profiles were reported.")
            except ValueError:
                pass
        return CheckResult("Firewall", "Unknown", "info", "Windows firewall status could not be read without changing the system.")

    if system == "Darwin":
        tool = "/usr/libexec/ApplicationFirewall/socketfilterfw"
        if os.path.exists(tool):
            code, output = _run([tool, "--getglobalstate"])
            if code == 0 and output:
                lowered = output.lower()
                if "disabled" in lowered:
                    return CheckResult("Firewall", "Disabled", "warn", "macOS application firewall appears disabled.")
                if "enabled" in lowered:
                    return CheckResult("Firewall", "Enabled", "ok", output)
        return CheckResult("Firewall", "Unknown", "info", "macOS firewall status was unavailable.")

    if system == "Linux":
        if shutil.which("ufw"):
            code, output = _run(["ufw", "status"])
            if code == 0 and output:
                lowered = output.lower()
                if "status: active" in lowered:
                    return CheckResult("Firewall", "Active", "ok", "UFW reports an active firewall.")
                if "status: inactive" in lowered:
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

    powershell = _powershell_command()
    if not powershell:
        return CheckResult("Built-in protection", "Unknown", "info", "PowerShell was not available to read Defender status.")

    code, output = _run([
        powershell,
        "-NoProfile",
        "-Command",
        "$s=Get-MpComputerStatus; Write-Output ($s.AntivirusEnabled.ToString()+','+$s.RealTimeProtectionEnabled.ToString())",
    ])
    if code == 0 and output:
        parts = [part.strip().lower() for part in output.splitlines()[-1].split(",")]
        if len(parts) == 2 and parts[0] == "true" and parts[1] == "true":
            return CheckResult("Built-in protection", "Active", "ok", "Microsoft Defender antivirus and real-time protection report enabled.")
        if len(parts) == 2:
            return CheckResult("Built-in protection", "Needs review", "warn", "Microsoft Defender did not report both antivirus and real-time protection enabled.")

    return CheckResult("Built-in protection", "Unknown", "info", "Defender status could not be read.")


def run_local_checks() -> List[CheckResult]:
    try:
        hostname = socket.gethostname() or "Unavailable"
    except OSError:
        hostname = "Unavailable"

    try:
        os_name = f"{platform.system()} {platform.release()}".strip() or "Unknown"
        platform_detail = platform.platform() or "Platform details unavailable."
    except Exception:
        os_name = "Unknown"
        platform_detail = "Platform details unavailable."

    results = [
        CheckResult("Device", platform.node() or hostname or "Unknown", "info", "Local device name."),
        CheckResult("Operating system", os_name, "info", platform_detail),
        CheckResult("Python", platform.python_version(), "info", "Runtime used by Neon Shield."),
        _safe_check("Disk free", _disk_check),
        _safe_check("Firewall", _firewall_check),
        _safe_check("Built-in protection", _defender_check),
        CheckResult("Local hostname", hostname, "info", "Shown locally only; Neon Shield does not transmit this value."),
    ]
    return results
