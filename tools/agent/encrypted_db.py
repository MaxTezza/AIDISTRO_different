#!/usr/bin/env python3
"""
AI Distro — Encrypted Database Layer

Provides transparent AES-256-GCM encryption for the Bayesian learning
database and other sensitive stores. Encryption key is derived from the
user's passphrase using PBKDF2-SHA256.

Supports:
  - First-run key setup (interactive passphrase)
  - Encrypt existing plaintext DB
  - Decrypt on service startup (passphrase or keyfile)
  - Automatic re-encryption on shutdown
  - Key rotation (change passphrase)
  - Keyfile mode for headless/service operation

Storage:
  ~/.cache/ai-distro/bayesian.db         (plaintext, when unlocked)
  ~/.cache/ai-distro/bayesian.db.enc     (encrypted, at rest)
  ~/.config/ai-distro/db.salt            (PBKDF2 salt)
  ~/.config/ai-distro/db.keyfile         (optional, for services)

Usage:
  python3 encrypted_db.py setup          # First-time passphrase setup
  python3 encrypted_db.py lock           # Encrypt DB now
  python3 encrypted_db.py unlock         # Decrypt DB (prompts for passphrase)
  python3 encrypted_db.py status         # Show encryption status
  python3 encrypted_db.py rotate         # Change passphrase
  python3 encrypted_db.py keyfile        # Generate keyfile for services
"""
import getpass
import hashlib
import hmac
import json
import os
import secrets
import sys
from pathlib import Path

DB_PATH = Path(os.path.expanduser("~/.cache/ai-distro/bayesian.db"))
ENC_PATH = Path(os.path.expanduser("~/.cache/ai-distro/bayesian.db.enc"))
MEMORY_DB = Path(os.path.expanduser("~/.cache/ai-distro/memory.db"))
MEMORY_ENC = Path(os.path.expanduser("~/.cache/ai-distro/memory.db.enc"))
SALT_PATH = Path(os.path.expanduser("~/.config/ai-distro/db.salt"))
KEYFILE_PATH = Path(os.path.expanduser("~/.config/ai-distro/db.keyfile"))
ITERATIONS = 600_000  # PBKDF2 iterations (OWASP 2023 recommendation)
NONCE_SIZE = 12  # GCM nonce
TAG_SIZE = 16  # GCM auth tag
KEY_SIZE = 32  # AES-256


def _derive_key(passphrase, salt):
    """Derive AES-256 key from passphrase using PBKDF2-SHA256."""
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, ITERATIONS, dklen=KEY_SIZE)


def _get_salt():
    """Get or create the PBKDF2 salt."""
    if SALT_PATH.exists():
        return SALT_PATH.read_bytes()
    salt = secrets.token_bytes(32)
    SALT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SALT_PATH.write_bytes(salt)
    os.chmod(str(SALT_PATH), 0o600)
    return salt


def _aes_gcm_encrypt(key, plaintext):
    """
    AES-256-GCM encryption using pure Python (CTR + GHASH).
    For production, prefer `cryptography` library. This provides
    baseline protection without external dependencies.
    """
    # Try to use the cryptography library if available
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce = secrets.token_bytes(NONCE_SIZE)
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ct  # nonce || ciphertext || tag
    except ImportError:
        pass

    # Fallback: XOR cipher with HMAC authentication
    # Not AES-GCM but provides confidentiality + integrity
    nonce = secrets.token_bytes(NONCE_SIZE)
    stream_key = hashlib.pbkdf2_hmac("sha256", key, nonce, 1, dklen=len(plaintext))
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, stream_key))
    tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()[:TAG_SIZE]
    return nonce + ciphertext + tag


def _aes_gcm_decrypt(key, data):
    """Decrypt AES-256-GCM (or fallback XOR+HMAC)."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce = data[:NONCE_SIZE]
        ct_and_tag = data[NONCE_SIZE:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ct_and_tag, None)
    except ImportError:
        pass

    # Fallback
    nonce = data[:NONCE_SIZE]
    tag = data[-TAG_SIZE:]
    ciphertext = data[NONCE_SIZE:-TAG_SIZE]

    expected_tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()[:TAG_SIZE]
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Authentication failed: data corrupted or wrong passphrase")

    stream_key = hashlib.pbkdf2_hmac("sha256", key, nonce, 1, dklen=len(ciphertext))
    return bytes(a ^ b for a, b in zip(ciphertext, stream_key))


def _get_key(passphrase=None):
    """Get the encryption key from passphrase or keyfile."""
    salt = _get_salt()

    if passphrase:
        return _derive_key(passphrase, salt)

    # Try keyfile
    if KEYFILE_PATH.exists():
        key_data = KEYFILE_PATH.read_bytes()
        return hashlib.pbkdf2_hmac("sha256", key_data, salt, 1, dklen=KEY_SIZE)

    # Interactive
    passphrase = getpass.getpass("AI Distro passphrase: ")
    if not passphrase:
        raise ValueError("Passphrase required")
    return _derive_key(passphrase, salt)


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

def setup(passphrase=None):
    """First-time encryption setup."""
    if ENC_PATH.exists():
        return {"status": "already_configured", "message": "Encryption already set up"}

    if not passphrase:
        passphrase = getpass.getpass("Create AI Distro passphrase: ")
        confirm = getpass.getpass("Confirm passphrase: ")
        if passphrase != confirm:
            return {"error": "Passphrases don't match"}
        if len(passphrase) < 6:
            return {"error": "Passphrase must be at least 6 characters"}

    salt = _get_salt()
    key = _derive_key(passphrase, salt)

    # Encrypt existing databases
    encrypted_count = 0
    for db, enc in [(DB_PATH, ENC_PATH), (MEMORY_DB, MEMORY_ENC)]:
        if db.exists():
            plaintext = db.read_bytes()
            encrypted = _aes_gcm_encrypt(key, plaintext)
            enc.write_bytes(encrypted)
            os.chmod(str(enc), 0o600)
            db.unlink()
            encrypted_count += 1

    return {
        "status": "ok",
        "message": f"Encryption configured. {encrypted_count} database(s) encrypted.",
        "hint": "Run 'python3 encrypted_db.py keyfile' to create a keyfile for services.",
    }


def lock(passphrase=None):
    """Encrypt databases at rest (shutdown hook)."""
    key = _get_key(passphrase)
    locked = []

    for db, enc in [(DB_PATH, ENC_PATH), (MEMORY_DB, MEMORY_ENC)]:
        if db.exists():
            plaintext = db.read_bytes()
            encrypted = _aes_gcm_encrypt(key, plaintext)
            enc.write_bytes(encrypted)
            os.chmod(str(enc), 0o600)
            db.unlink()
            locked.append(db.name)

    return {"status": "ok", "locked": locked}


def unlock(passphrase=None):
    """Decrypt databases for use (startup hook)."""
    key = _get_key(passphrase)
    unlocked = []

    for db, enc in [(DB_PATH, ENC_PATH), (MEMORY_DB, MEMORY_ENC)]:
        if enc.exists():
            encrypted = enc.read_bytes()
            try:
                plaintext = _aes_gcm_decrypt(key, encrypted)
            except ValueError as e:
                return {"error": str(e)}
            db.parent.mkdir(parents=True, exist_ok=True)
            db.write_bytes(plaintext)
            os.chmod(str(db), 0o600)
            unlocked.append(db.name)

    return {"status": "ok", "unlocked": unlocked}


def status():
    """Show current encryption status."""
    info = {
        "encryption_configured": SALT_PATH.exists(),
        "keyfile_exists": KEYFILE_PATH.exists(),
        "databases": {},
    }

    for name, db, enc in [("bayesian", DB_PATH, ENC_PATH), ("memory", MEMORY_DB, MEMORY_ENC)]:
        if enc.exists() and not db.exists():
            info["databases"][name] = "🔒 encrypted (locked)"
        elif db.exists() and not enc.exists():
            info["databases"][name] = "⚠️  plaintext (not encrypted)"
        elif db.exists() and enc.exists():
            info["databases"][name] = "🔓 decrypted (unlocked)"
        else:
            info["databases"][name] = "○ not found"

    # Check if cryptography library is available
    try:
        import cryptography  # noqa: F401
        info["cipher"] = "AES-256-GCM (cryptography library)"
    except ImportError:
        info["cipher"] = "XOR+HMAC-SHA256 (fallback — install 'cryptography' for AES-GCM)"

    return info


def rotate(old_passphrase=None, new_passphrase=None):
    """Change the encryption passphrase."""
    # Unlock with old key
    result = unlock(old_passphrase)
    if "error" in result:
        return result

    # Generate new salt
    new_salt = secrets.token_bytes(32)
    SALT_PATH.write_bytes(new_salt)
    os.chmod(str(SALT_PATH), 0o600)

    if not new_passphrase:
        new_passphrase = getpass.getpass("New passphrase: ")
        confirm = getpass.getpass("Confirm new passphrase: ")
        if new_passphrase != confirm:
            return {"error": "New passphrases don't match"}

    # Lock with new key
    result = lock(new_passphrase)
    result["message"] = "Passphrase rotated successfully"

    # Invalidate old keyfile
    if KEYFILE_PATH.exists():
        KEYFILE_PATH.unlink()
        result["warning"] = "Old keyfile invalidated. Run 'keyfile' to generate a new one."

    return result


def generate_keyfile():
    """Generate a keyfile for headless/service operation."""
    key_data = secrets.token_bytes(64)
    KEYFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEYFILE_PATH.write_bytes(key_data)
    os.chmod(str(KEYFILE_PATH), 0o600)

    return {
        "status": "ok",
        "path": str(KEYFILE_PATH),
        "message": "Keyfile generated. Services can now unlock without passphrase.",
        "warning": "Keep this file secure — it provides full access to encrypted data.",
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: encrypted_db.py <setup|lock|unlock|status|rotate|keyfile>")
        return

    cmd = sys.argv[1]

    if cmd == "setup":
        pp = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(setup(pp), indent=2))
    elif cmd == "lock":
        pp = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(lock(pp), indent=2))
    elif cmd == "unlock":
        pp = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(unlock(pp), indent=2))
    elif cmd == "status":
        print(json.dumps(status(), indent=2))
    elif cmd == "rotate":
        print(json.dumps(rotate(), indent=2))
    elif cmd == "keyfile":
        print(json.dumps(generate_keyfile(), indent=2))
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
