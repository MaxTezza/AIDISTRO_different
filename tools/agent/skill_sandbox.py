#!/usr/bin/env python3
"""
AI Distro — Skill Sandbox

Executes skills inside a security sandbox with permission tiers.
Uses bubblewrap (bwrap) for filesystem/network isolation, falling back
to subprocess restrictions when bwrap is unavailable.

Permission Tiers:
  TIER_0 (minimal)   — Read-only filesystem, no network, no home access
  TIER_1 (standard)  — Read-only FS, network allowed, no home write
  TIER_2 (elevated)  — Read-write home, network allowed
  TIER_3 (full)      — Full access (requires explicit user approval)

Skills declare required permissions in their JSON manifest:
  "permissions": ["network", "filesystem_read", "filesystem_write", "home_dir", "exec"]

Usage:
  python3 skill_sandbox.py run <skill_name> [args...]
  python3 skill_sandbox.py check <skill_name>       # Show required permissions
  python3 skill_sandbox.py approve <skill_name>      # Approve for elevated tier
  python3 skill_sandbox.py policy                    # Show current policy
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SKILLS_DIR = Path(os.path.expanduser("~/.config/ai-distro/skills"))
CORE_SKILLS_DIR = Path(__file__).parent.parent.parent / "src" / "skills" / "core"
POLICY_FILE = Path(os.path.expanduser("~/.config/ai-distro/sandbox_policy.json"))
AUDIT_LOG = Path(os.path.expanduser("~/.cache/ai-distro/sandbox_audit.jsonl"))

# Permission → tier mapping
PERMISSION_TIERS = {
    "network": 1,
    "filesystem_read": 0,
    "filesystem_write": 2,
    "home_dir": 2,
    "exec": 2,
    "system_admin": 3,
    "hardware_control": 3,
    "camera": 3,
    "microphone": 1,
}


def _has_bwrap():
    """Check if bubblewrap is available."""
    return shutil.which("bwrap") is not None


def _has_firejail():
    """Check if firejail is available."""
    return shutil.which("firejail") is not None


def _load_policy():
    """Load the sandbox approval policy."""
    if POLICY_FILE.exists():
        with open(POLICY_FILE) as f:
            return json.load(f)
    return {"approved_skills": {}, "default_tier": 1, "auto_approve_below": 1}


def _save_policy(policy):
    POLICY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(POLICY_FILE, "w") as f:
        json.dump(policy, f, indent=2)


def _audit(skill_name, action, details=None):
    """Append to sandbox audit log."""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "skill": skill_name,
        "action": action,
        "details": details,
    }
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _find_skill_manifest(skill_name):
    """Find a skill's JSON manifest."""
    for search_dir in [SKILLS_DIR, CORE_SKILLS_DIR]:
        if not search_dir.exists():
            continue
        manifest = search_dir / f"{skill_name}.json"
        if manifest.exists():
            with open(manifest) as f:
                return json.load(f)
        # Search subdirectories
        for sub in search_dir.rglob(f"{skill_name}.json"):
            with open(sub) as f:
                return json.load(f)
    return None


def _compute_tier(permissions):
    """Compute the minimum required tier for a set of permissions."""
    if not permissions:
        return 0
    return max(PERMISSION_TIERS.get(p, 3) for p in permissions)


def _build_bwrap_args(tier, script_path):
    """Build bubblewrap arguments for the given security tier."""
    args = ["bwrap"]

    # Base: new namespaces
    args += ["--unshare-pid", "--unshare-uts", "--unshare-ipc"]
    args += ["--die-with-parent"]
    args += ["--proc", "/proc"]
    args += ["--dev", "/dev"]
    args += ["--tmpfs", "/tmp"]

    if tier == 0:
        # Minimal: read-only root, no network, no home
        args += ["--unshare-net"]
        args += ["--ro-bind", "/usr", "/usr"]
        args += ["--ro-bind", "/lib", "/lib"]
        args += ["--ro-bind", "/lib64", "/lib64"]
        args += ["--ro-bind", "/etc", "/etc"]
        args += ["--ro-bind", "/bin", "/bin"]
        args += ["--ro-bind", "/sbin", "/sbin"]
        args += ["--ro-bind", str(script_path), str(script_path)]

    elif tier == 1:
        # Standard: read-only, network allowed
        args += ["--ro-bind", "/usr", "/usr"]
        args += ["--ro-bind", "/lib", "/lib"]
        args += ["--ro-bind", "/lib64", "/lib64"]
        args += ["--ro-bind", "/etc", "/etc"]
        args += ["--ro-bind", "/bin", "/bin"]
        args += ["--ro-bind", "/sbin", "/sbin"]
        args += ["--ro-bind", str(script_path), str(script_path)]
        # Bind /run for DNS resolution
        if os.path.exists("/run/systemd/resolve"):
            args += ["--ro-bind", "/run/systemd/resolve", "/run/systemd/resolve"]

    elif tier == 2:
        # Elevated: read-write home, network
        home = os.path.expanduser("~")
        args += ["--ro-bind", "/usr", "/usr"]
        args += ["--ro-bind", "/lib", "/lib"]
        args += ["--ro-bind", "/lib64", "/lib64"]
        args += ["--ro-bind", "/etc", "/etc"]
        args += ["--ro-bind", "/bin", "/bin"]
        args += ["--ro-bind", "/sbin", "/sbin"]
        args += ["--bind", home, home]
        args += ["--ro-bind", str(script_path), str(script_path)]
        if os.path.exists("/run/systemd/resolve"):
            args += ["--ro-bind", "/run/systemd/resolve", "/run/systemd/resolve"]

    else:
        # Tier 3: full — just use bwrap for PID isolation
        args += ["--bind", "/", "/"]

    return args


def _build_firejail_args(tier, script_path):
    """Build firejail arguments as a fallback sandbox."""
    args = ["firejail", "--quiet", "--noprofile"]

    if tier == 0:
        args += ["--net=none", "--read-only=/", "--private"]
    elif tier == 1:
        args += ["--read-only=/", "--private"]
    elif tier == 2:
        args += ["--read-only=/usr", "--read-only=/etc"]
    # Tier 3: minimal firejail wrapping

    return args


def check_permissions(skill_name):
    """Check what permissions a skill requires and its tier."""
    manifest = _find_skill_manifest(skill_name)
    if not manifest:
        return {"error": f"Skill '{skill_name}' not found"}

    permissions = manifest.get("permissions", [])
    tier = _compute_tier(permissions)

    policy = _load_policy()
    approved = policy.get("approved_skills", {}).get(skill_name, {})

    return {
        "skill": skill_name,
        "permissions": permissions,
        "required_tier": tier,
        "approved": bool(approved),
        "approved_tier": approved.get("tier") if approved else None,
        "auto_approve": tier <= policy.get("auto_approve_below", 1),
    }


def approve_skill(skill_name, tier=None):
    """Approve a skill for elevated execution."""
    manifest = _find_skill_manifest(skill_name)
    if not manifest:
        return {"error": f"Skill '{skill_name}' not found"}

    permissions = manifest.get("permissions", [])
    required_tier = _compute_tier(permissions)
    approved_tier = tier if tier is not None else required_tier

    policy = _load_policy()
    policy.setdefault("approved_skills", {})[skill_name] = {
        "tier": approved_tier,
        "approved_at": datetime.now().isoformat(),
        "permissions": permissions,
    }
    _save_policy(policy)
    _audit(skill_name, "approved", {"tier": approved_tier})

    return {"status": "ok", "skill": skill_name, "tier": approved_tier}


def run_skill(skill_name, args=None):
    """Execute a skill inside the appropriate sandbox."""
    manifest = _find_skill_manifest(skill_name)
    if not manifest:
        return {"error": f"Skill '{skill_name}' not found"}

    permissions = manifest.get("permissions", [])
    required_tier = _compute_tier(permissions)

    # Check approval
    policy = _load_policy()
    auto_approve_limit = policy.get("auto_approve_below", 1)

    if required_tier > auto_approve_limit:
        approved = policy.get("approved_skills", {}).get(skill_name, {})
        if not approved or approved.get("tier", -1) < required_tier:
            _audit(skill_name, "blocked", {"required_tier": required_tier})
            return {
                "error": "permission_denied",
                "skill": skill_name,
                "required_tier": required_tier,
                "message": f"Skill '{skill_name}' requires tier {required_tier} but is not approved. "
                           f"Run: python3 skill_sandbox.py approve {skill_name}",
            }

    # Determine the script to execute
    handler = manifest.get("handler", "")
    if not handler:
        return {"error": f"Skill '{skill_name}' has no handler defined"}

    # Resolve handler path
    script_path = None
    for base in [Path(__file__).parent, SKILLS_DIR, CORE_SKILLS_DIR]:
        candidate = base / handler
        if candidate.exists():
            script_path = str(candidate)
            break
    if not script_path:
        # Try as absolute or relative
        if os.path.exists(handler):
            script_path = handler

    if not script_path:
        return {"error": f"Handler not found: {handler}"}

    # Build sandbox command
    cmd = []
    sandbox_type = "none"

    if _has_bwrap() and required_tier < 3:
        cmd = _build_bwrap_args(required_tier, script_path)
        sandbox_type = "bwrap"
    elif _has_firejail() and required_tier < 3:
        cmd = _build_firejail_args(required_tier, script_path)
        sandbox_type = "firejail"

    # Add the actual script invocation
    cmd += ["python3", script_path]
    if args:
        cmd += args

    _audit(skill_name, "execute", {
        "tier": required_tier,
        "sandbox": sandbox_type,
        "permissions": permissions,
    })

    # Execute
    try:
        env = os.environ.copy()
        env["AI_DISTRO_SANDBOX_TIER"] = str(required_tier)
        env["AI_DISTRO_SKILL_NAME"] = skill_name

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, env=env
        )

        _audit(skill_name, "completed", {
            "exit_code": result.returncode,
            "sandbox": sandbox_type,
        })

        return {
            "status": "ok" if result.returncode == 0 else "error",
            "skill": skill_name,
            "sandbox": sandbox_type,
            "tier": required_tier,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-1000:] if result.returncode != 0 else "",
            "exit_code": result.returncode,
        }

    except subprocess.TimeoutExpired:
        _audit(skill_name, "timeout", {"sandbox": sandbox_type})
        return {"error": "timeout", "skill": skill_name}
    except Exception as e:
        _audit(skill_name, "error", {"error": str(e)})
        return {"error": str(e)}


def show_policy():
    """Display the current sandbox policy."""
    policy = _load_policy()
    info = {
        "default_tier": policy.get("default_tier", 1),
        "auto_approve_below": policy.get("auto_approve_below", 1),
        "sandbox_available": {
            "bubblewrap": _has_bwrap(),
            "firejail": _has_firejail(),
        },
        "approved_skills": policy.get("approved_skills", {}),
        "tier_descriptions": {
            0: "Minimal — read-only FS, no network, no home",
            1: "Standard — read-only FS, network allowed",
            2: "Elevated — read-write home, network (requires approval)",
            3: "Full — unrestricted (requires explicit approval)",
        },
    }
    return info


def main():
    if len(sys.argv) < 2:
        print("Usage: skill_sandbox.py <run|check|approve|policy>")
        return

    cmd = sys.argv[1]

    if cmd == "run":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        extra = sys.argv[3:] if len(sys.argv) > 3 else []
        if not name:
            print("Usage: skill_sandbox.py run <skill_name> [args...]")
            return
        print(json.dumps(run_skill(name, extra), indent=2))

    elif cmd == "check":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        if not name:
            print("Usage: skill_sandbox.py check <skill_name>")
            return
        print(json.dumps(check_permissions(name), indent=2))

    elif cmd == "approve":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        tier = int(sys.argv[3]) if len(sys.argv) > 3 else None
        if not name:
            print("Usage: skill_sandbox.py approve <skill_name> [tier]")
            return
        print(json.dumps(approve_skill(name, tier), indent=2))

    elif cmd == "policy":
        print(json.dumps(show_policy(), indent=2))

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
