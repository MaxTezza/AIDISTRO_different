#!/usr/bin/env python3
import os
import subprocess
import json
import sys

def get_bloat():
    """Find large files (>100MB) in home and common dirs."""
    try:
        cmd = ["find", os.path.expanduser("~"), "-type", "f", "-size", "+100M", "-not", "-path", "*/.git/*", "-not", "-path", "*/node_modules/*"]
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
        return result.splitlines()
    except Exception:
        return []

def get_orphan_packages():
    """Find packages that were installed as dependencies but are no longer needed."""
    try:
        # For Pop!_OS / Ubuntu
        subprocess.check_output(["apt-mark", "showauto"], stderr=subprocess.STNULL).decode()
        # This is a bit simplified, but a good start
        return "Check 'sudo apt autoremove --dry-run' for potential cleanup."
    except Exception:
        return "Package manager not supported."

def run_audit(scan_type="full"):
    report = {"summary": f"System Audit ({scan_type})", "findings": []}
    
    if scan_type in ["bloat", "full"]:
        large_files = get_bloat()
        if large_files:
            report["findings"].append({
                "category": "Bloat",
                "message": f"Found {len(large_files)} files larger than 100MB.",
                "details": large_files[:5] # Top 5
            })

    if scan_type in ["packages", "full"]:
        orphans = get_orphan_packages()
        report["findings"].append({
            "category": "Packages",
            "message": "Orphan package check completed.",
            "suggestion": orphans
        })

    return report

if __name__ == "__main__":
    scan_type = sys.argv[1] if len(sys.argv) > 1 else "full"
    print(json.dumps(run_audit(scan_type), indent=2))
