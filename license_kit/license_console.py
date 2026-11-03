#!/usr/bin/env python3
"""
BioSecure AI — Standalone Developer License Kit (license_console.py)

A completely self-contained terminal console and CLI tool for generating,
issuing, and cryptographically verifying Ed25519 software licenses.
Features dynamic terminal themes with custom font colors and background styles.

This kit can be kept inside this repository or moved to an isolated private
workstation/USB drive to keep developer private keys completely separate from
production code.

Usage:
    python license_console.py               # Launch Interactive Terminal Console
    python license_console.py ui            # Launch Interactive Terminal Console
    python license_console.py issue ...     # Scriptable CLI: issue license
    python license_console.py inspect ...   # Scriptable CLI: inspect license
    python license_console.py generate-keys # Scriptable CLI: generate keypair
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, Optional, Tuple
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# Paths relative to this standalone kit directory
KIT_DIR = Path(__file__).resolve().parent
DEFAULT_PRIV_KEY = KIT_DIR / "developer_private_key.pem"
DEFAULT_PUB_KEY = KIT_DIR / "license_public_key.pem"
OUTPUT_DIR = KIT_DIR / "output"
THEME_FILE = KIT_DIR / ".theme"

# Optional parent project detection (if kit resides inside repo)
PARENT_APP_DIR = KIT_DIR.parent
PARENT_APP_PUB_KEY = PARENT_APP_DIR / "src" / "security" / "license_public_key.pem"
PARENT_APP_LICENSE = PARENT_APP_DIR / ".license"
PARENT_APP_STATE = PARENT_APP_DIR / ".license_state"


# =============================================================================
# ANSI Styling & Dynamic Font / Background Color Themes
# =============================================================================

class Style:
    """ANSI color formatting with terminal detection."""
    ENABLED = sys.stdout.isatty() and not os.environ.get("NO_COLOR")

    RESET = "\033[0m" if ENABLED else ""
    # Explicitly combine bold with high-intensity bright white (97) so bare BOLD is NEVER black
    BOLD = "\033[1;97m" if ENABLED else ""
    BOLD_WHITE = "\033[1;97m" if ENABLED else ""
    BOLD_CYAN = "\033[1;96m" if ENABLED else ""
    BOLD_YELLOW = "\033[1;93m" if ENABLED else ""
    BOLD_GREEN = "\033[1;92m" if ENABLED else ""
    BOLD_MAGENTA = "\033[1;95m" if ENABLED else ""
    DIM = "\033[2;37m" if ENABLED else ""
    UNDERLINE = "\033[4m" if ENABLED else ""

    # Foreground font colors
    BLACK = "\033[30m" if ENABLED else ""
    RED = "\033[91m" if ENABLED else ""
    GREEN = "\033[92m" if ENABLED else ""
    YELLOW = "\033[93m" if ENABLED else ""
    BLUE = "\033[94m" if ENABLED else ""
    MAGENTA = "\033[95m" if ENABLED else ""
    CYAN = "\033[96m" if ENABLED else ""
    WHITE = "\033[97m" if ENABLED else ""
    GOLD = "\033[38;5;220m" if ENABLED else ""

    # Solid background colors
    BG_BLACK = "\033[40m" if ENABLED else ""
    BG_RED = "\033[41m" if ENABLED else ""
    BG_GREEN = "\033[42m" if ENABLED else ""
    BG_YELLOW = "\033[43m" if ENABLED else ""
    BG_BLUE = "\033[44m" if ENABLED else ""
    BG_MAGENTA = "\033[45m" if ENABLED else ""
    BG_CYAN = "\033[46m" if ENABLED else ""
    BG_WHITE = "\033[47m" if ENABLED else ""
    BG_DARK_GRAY = "\033[100m" if ENABLED else ""

    # Status Badges with Background Colors (Always use crisp bold white text on high-contrast backgrounds)
    BADGE_OK = "\033[42;97;1m" if ENABLED else ""         # Green background, white text
    BADGE_WARN = "\033[48;5;208;97;1m" if ENABLED else "" # Amber/Orange background, white text
    BADGE_ERR = "\033[41;97;1m" if ENABLED else ""        # Red background, white text
    BADGE_INFO = "\033[46;97;1m" if ENABLED else ""       # Cyan background, white text
    BADGE_SECRET = "\033[45;97;1m" if ENABLED else ""     # Magenta background, white text


# Available Font & Background Palettes
THEMES: Dict[str, Dict[str, str]] = {
    "midnight": {
        "name": "Midnight Executive (Deep Blue & Gold)",
        "border": "\033[94m" if Style.ENABLED else "",
        "banner_bg": "\033[44m" if Style.ENABLED else "",
        "banner_fg": "\033[97;1m" if Style.ENABLED else "",
        "sub_bg": "\033[100m" if Style.ENABLED else "",
        "sub_fg": "\033[93m" if Style.ENABLED else "",
        "accent": "\033[93m" if Style.ENABLED else "",
        "primary": "\033[96m" if Style.ENABLED else "",
        "key_tag": "\033[44;97;1m" if Style.ENABLED else "",
        "card_header": "\033[48;5;18;97;1m" if Style.ENABLED else "",
        "prompt": "\033[96;1m" if Style.ENABLED else "",
    },
    "cyber": {
        "name": "Cyber Neon (Electric Cyan & Magenta)",
        "border": "\033[96m" if Style.ENABLED else "",
        "banner_bg": "\033[46m" if Style.ENABLED else "",
        "banner_fg": "\033[97;1m" if Style.ENABLED else "",
        "sub_bg": "\033[100m" if Style.ENABLED else "",
        "sub_fg": "\033[95;1m" if Style.ENABLED else "",
        "accent": "\033[95m" if Style.ENABLED else "",
        "primary": "\033[96m" if Style.ENABLED else "",
        "key_tag": "\033[46;97;1m" if Style.ENABLED else "",
        "card_header": "\033[48;5;24;97;1m" if Style.ENABLED else "",
        "prompt": "\033[95;1m" if Style.ENABLED else "",
    },
    "matrix": {
        "name": "Matrix Terminal (Phosphor Emerald)",
        "border": "\033[92m" if Style.ENABLED else "",
        "banner_bg": "\033[42m" if Style.ENABLED else "",
        "banner_fg": "\033[97;1m" if Style.ENABLED else "",
        "sub_bg": "\033[100m" if Style.ENABLED else "",
        "sub_fg": "\033[92;1m" if Style.ENABLED else "",
        "accent": "\033[92;1m" if Style.ENABLED else "",
        "primary": "\033[92m" if Style.ENABLED else "",
        "key_tag": "\033[42;97;1m" if Style.ENABLED else "",
        "card_header": "\033[48;5;22;97;1m" if Style.ENABLED else "",
        "prompt": "\033[92;1m" if Style.ENABLED else "",
    },
    "sunset": {
        "name": "Sunset Cyberpunk (Vivid Magenta & Amber)",
        "border": "\033[95m" if Style.ENABLED else "",
        "banner_bg": "\033[45m" if Style.ENABLED else "",
        "banner_fg": "\033[97;1m" if Style.ENABLED else "",
        "sub_bg": "\033[100m" if Style.ENABLED else "",
        "sub_fg": "\033[93;1m" if Style.ENABLED else "",
        "accent": "\033[93m" if Style.ENABLED else "",
        "primary": "\033[95m" if Style.ENABLED else "",
        "key_tag": "\033[45;97;1m" if Style.ENABLED else "",
        "card_header": "\033[48;5;53;97;1m" if Style.ENABLED else "",
        "prompt": "\033[93;1m" if Style.ENABLED else "",
    },
    "slate": {
        "name": "Dark Slate (High-Contrast Monochrome)",
        "border": "\033[37m" if Style.ENABLED else "",
        "banner_bg": "\033[100m" if Style.ENABLED else "",
        "banner_fg": "\033[97;1m" if Style.ENABLED else "",
        "sub_bg": "\033[40m" if Style.ENABLED else "",
        "sub_fg": "\033[37m" if Style.ENABLED else "",
        "accent": "\033[97;1m" if Style.ENABLED else "",
        "primary": "\033[97m" if Style.ENABLED else "",
        "key_tag": "\033[100;97;1m" if Style.ENABLED else "",
        "card_header": "\033[48;5;236;97;1m" if Style.ENABLED else "",
        "prompt": "\033[97;1m" if Style.ENABLED else "",
    },
}

_CURRENT_THEME_KEY = "midnight"


def load_theme() -> str:
    """Load persisted theme preference from .theme file."""
    global _CURRENT_THEME_KEY
    if THEME_FILE.is_file():
        try:
            saved = THEME_FILE.read_text(encoding="utf-8").strip().lower()
            if saved in THEMES:
                _CURRENT_THEME_KEY = saved
        except Exception:
            pass
    return _CURRENT_THEME_KEY


def save_theme(theme_key: str) -> None:
    """Persist theme preference."""
    global _CURRENT_THEME_KEY
    if theme_key in THEMES:
        _CURRENT_THEME_KEY = theme_key
        try:
            THEME_FILE.write_text(theme_key + "\n", encoding="utf-8")
        except Exception:
            pass


def get_current_theme() -> Dict[str, str]:
    """Retrieve active theme styling dictionary."""
    return THEMES.get(_CURRENT_THEME_KEY, THEMES["midnight"])


def clear_screen() -> None:
    """Clear terminal screen if running interactively."""
    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")


def print_banner(subtitle: str = "Developer Licensing & Cryptographic Access Control") -> None:
    """Print application header banner with full background color styling."""
    t = get_current_theme()
    w = 72
    border = "═" * (w - 2)
    title_str = "BIOSECURE AI — DEVELOPER LICENSING CONSOLE (STANDALONE)"
    sub_centered = subtitle.center(w - 2)

    print(f"{t['border']}╔{border}╗{Style.RESET}")
    print(f"{t['border']}║{t['banner_bg']}{t['banner_fg']}{title_str.center(w - 2)}{Style.RESET}{t['border']}║{Style.RESET}")
    print(f"{t['border']}║{t['sub_bg']}{t['sub_fg']}{sub_centered}{Style.RESET}{t['border']}║{Style.RESET}")
    print(f"{t['border']}╚{border}╝{Style.RESET}")


def get_input(prompt_text: str, default: Optional[str] = None, allow_empty: bool = False) -> str:
    """Prompt user with optional default value and styled prompt."""
    t = get_current_theme()
    if default is not None:
        display_prompt = f"{t['prompt']}{prompt_text}{Style.RESET} {Style.DIM}[{default}]{Style.RESET}: "
    else:
        display_prompt = f"{t['prompt']}{prompt_text}{Style.RESET}: "

    while True:
        try:
            val = input(display_prompt).strip()
            if not val and default is not None:
                return default
            if not val and not allow_empty:
                print(f"{Style.RED}⚠ Value cannot be empty.{Style.RESET}")
                continue
            return val
        except (KeyboardInterrupt, EOFError):
            print("\n")
            raise


def pause() -> None:
    """Pause until user presses Enter."""
    try:
        input(f"\n{Style.DIM}Press Enter to return to menu...{Style.RESET}")
    except (KeyboardInterrupt, EOFError):
        print("")


def slugify(name: str) -> str:
    """Create filesystem-friendly slug for filenames."""
    s = re.sub(r"[^\w\s-]", "", name).strip().lower()
    return re.sub(r"[-\s]+", "_", s) or "client"


# =============================================================================
# Cryptographic Operations
# =============================================================================

def generate_keypair(
    priv_path: Path,
    pub_path: Path,
    force: bool = False,
    sync_to_app: bool = True,
) -> Tuple[bool, str]:
    """Generate Ed25519 private and public keys."""
    if priv_path.exists() and not force:
        return False, f"Private key already exists at {priv_path}. Use overwrite option to replace."

    priv_path.parent.mkdir(parents=True, exist_ok=True)
    pub_path.parent.mkdir(parents=True, exist_ok=True)

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    priv_path.write_bytes(priv_pem)
    try:
        os.chmod(priv_path, 0o600)
    except OSError:
        pass

    pub_path.write_bytes(pub_pem)

    # Sync public key to parent application if it exists
    if sync_to_app and PARENT_APP_PUB_KEY.parent.exists():
        try:
            PARENT_APP_PUB_KEY.write_bytes(pub_pem)
        except OSError:
            pass

    return True, "Keypair successfully generated."


def issue_license_token(
    customer: str,
    priv_key_path: Path,
    output_path: Path,
    days: Optional[int] = None,
    expires_at: Optional[datetime] = None,
    license_id: Optional[str] = None,
    sync_to_app: bool = False,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Sign and create a .license token file."""
    if not priv_key_path.is_file():
        return False, f"Developer private key not found at {priv_key_path}.", {}

    try:
        priv_bytes = priv_key_path.read_bytes()
        private_key = serialization.load_pem_private_key(priv_bytes, password=None)
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            return False, "Private key file is not an Ed25519 key.", {}
    except Exception as exc:
        return False, f"Failed to load private key: {exc}", {}

    now_utc = datetime.now(timezone.utc)
    if expires_at is None:
        if days is None or days <= 0:
            return False, "Duration must be positive number of days.", {}
        expires_at = now_utc + timedelta(days=days)

    if expires_at <= now_utc:
        return False, f"Expiration date {expires_at.isoformat()} is in the past.", {}

    lic_id = license_id.strip() if license_id else uuid.uuid4().hex
    payload = {
        "customer": customer.strip(),
        "license_id": lic_id,
        "issued_at": now_utc.isoformat(),
        "expires_at": expires_at.isoformat(),
        "version": 1,
    }

    payload_canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = private_key.sign(payload_canonical)

    envelope = {
        "payload": payload,
        "signature": base64.b64encode(signature).decode("utf-8"),
    }
    raw_envelope = json.dumps(envelope, sort_keys=True, indent=2).encode("utf-8")
    encoded_license = base64.b64encode(raw_envelope).decode("utf-8")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(encoded_license + "\n", encoding="utf-8")

    # Optionally copy directly to parent app's .license
    if sync_to_app and PARENT_APP_DIR.is_dir():
        try:
            PARENT_APP_LICENSE.write_text(encoded_license + "\n", encoding="utf-8")
        except OSError:
            pass

    return True, "License generated successfully.", payload


def inspect_license_file(
    lic_path: Path,
    pub_path: Path,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Inspect and cryptographically verify a .license token."""
    if not lic_path.is_file():
        return False, f"License file not found at {lic_path}.", {}

    if not pub_path.is_file():
        return False, f"Public key not found at {pub_path}.", {}

    try:
        raw_b64 = lic_path.read_text(encoding="utf-8").strip()
        raw_json = base64.b64decode(raw_b64)
        envelope = json.loads(raw_json)
        payload = envelope["payload"]
        signature = base64.b64decode(envelope["signature"])
    except Exception as exc:
        return False, f"Error decoding license file format: {exc}", {}

    try:
        pub_bytes = pub_path.read_bytes()
        public_key = serialization.load_pem_public_key(pub_bytes)
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            return False, "Public key file is not an Ed25519 key.", {}
    except Exception as exc:
        return False, f"Error loading public key: {exc}", {}

    payload_canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    try:
        public_key.verify(signature, payload_canonical)
    except InvalidSignature:
        return False, "SIGNATURE INVALID: Signature does not match public key (tampered or forged)!", payload

    now_utc = datetime.now(timezone.utc)
    expires_at = datetime.fromisoformat(payload["expires_at"].replace("Z", "+00:00"))
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    payload["_is_expired"] = now_utc > expires_at
    payload["_remaining_seconds"] = (expires_at - now_utc).total_seconds()
    return True, "VALID", payload


# =============================================================================
# Dashboard & Interactive Wizards
# =============================================================================

def get_system_status() -> Dict[str, Any]:
    """Inspect local kit status and optional linked app status."""
    has_priv = DEFAULT_PRIV_KEY.is_file()
    has_pub = DEFAULT_PUB_KEY.is_file()

    active_tokens: list[Path] = []
    if OUTPUT_DIR.is_dir():
        active_tokens = list(OUTPUT_DIR.glob("*.license"))

    app_linked = PARENT_APP_DIR.is_dir() and PARENT_APP_PUB_KEY.exists()
    return {
        "has_priv": has_priv,
        "has_pub": has_pub,
        "token_count": len(active_tokens),
        "app_linked": app_linked,
    }


def render_dashboard() -> None:
    """Render the status dashboard with styled font and background badges."""
    t = get_current_theme()
    status = get_system_status()

    priv_badge = f"{Style.BADGE_OK} READY (0o600 Confidential) {Style.RESET}" if status["has_priv"] else f"{Style.BADGE_ERR} MISSING (Run Option 3) {Style.RESET}"
    pub_badge = f"{Style.BADGE_OK} READY (Public Verifier) {Style.RESET}" if status["has_pub"] else f"{Style.BADGE_ERR} MISSING {Style.RESET}"
    linked_badge = f"{Style.BADGE_INFO} DETECTED (Synced with App) {Style.RESET}" if status["app_linked"] else f"{Style.DIM}Standalone Mode (Isolated){Style.RESET}"

    print(f"\n{t['border']}─── {Style.BOLD}KIT ENVIRONMENT STATUS & SECURITY TIERS{Style.RESET} {t['border']}{'─' * 28}{Style.RESET}")
    print(f" ├─ Private Key (Secret) : {priv_badge} {Style.DIM}({DEFAULT_PRIV_KEY.name}){Style.RESET}")
    print(f" ├─ Public Key (Verifier): {pub_badge} {Style.DIM}({DEFAULT_PUB_KEY.name}){Style.RESET}")
    print(f" ├─ Issued Customer Files: {t['accent']}{status['token_count']} tokens{Style.RESET} {Style.DIM}in license_kit/output/{Style.RESET}")
    print(f" ├─ Application Linkage  : {linked_badge}")
    print(f" └─ Active Color Theme   : {t['accent']}{t['name']}{Style.RESET}")
    print(f"{t['border']}────────────────────────────────────────────────────────────────────────{Style.RESET}")


def wizard_issue_license() -> None:
    """Interactive wizard for issuing a signed license file."""
    t = get_current_theme()
    clear_screen()
    print_banner("Issue Client License Token")

    if not DEFAULT_PRIV_KEY.is_file():
        print(f"\n{Style.BADGE_ERR} ERROR {Style.RESET} {Style.BOLD}Developer private key not found in license_kit!{Style.RESET}")
        print(f"Please run {t['accent']}Option 3 (Generate / Rotate Developer Keypair){Style.RESET} first.")
        pause()
        return

    print(f"\n{t['accent']}Step 1: Client & Organization Details{Style.RESET}")
    customer = get_input("Client / Organization Name (e.g. 'Apex University')")

    print(f"\n{t['accent']}{Style.BOLD}Step 2: License Duration Preset{Style.RESET}")
    print(f"  {t['key_tag']} 1 {Style.RESET} {Style.BOLD_WHITE}7 Days{Style.RESET}   {Style.DIM}- Trial / Demo Period{Style.RESET}")
    print(f"  {t['key_tag']} 2 {Style.RESET} {Style.BOLD_WHITE}14 Days{Style.RESET}  {Style.DIM}- Standard 2-Week Pilot{Style.RESET}")
    print(f"  {t['key_tag']} 3 {Style.RESET} {Style.BOLD_WHITE}30 Days{Style.RESET}  {Style.DIM}- Monthly Lease / Milestone Delivery{Style.RESET}")
    print(f"  {t['key_tag']} 4 {Style.RESET} {Style.BOLD_WHITE}90 Days{Style.RESET}  {Style.DIM}- Quarterly Contract{Style.RESET}")
    print(f"  {t['key_tag']} 5 {Style.RESET} {Style.BOLD_WHITE}365 Days{Style.RESET} {Style.DIM}- Full Annual License{Style.RESET}")
    print(f"  {t['key_tag']} 6 {Style.RESET} {Style.BOLD_WHITE}Custom Days{Style.RESET}")
    print(f"  {t['key_tag']} 7 {Style.RESET} {Style.BOLD_WHITE}Exact Date{Style.RESET}  {Style.DIM}(YYYY-MM-DD){Style.RESET}")

    days_selected: Optional[int] = None
    expires_dt: Optional[datetime] = None

    while True:
        choice = get_input("Select duration option", default="3")
        if choice == "1":
            days_selected = 7
            break
        elif choice == "2":
            days_selected = 14
            break
        elif choice == "3":
            days_selected = 30
            break
        elif choice == "4":
            days_selected = 90
            break
        elif choice == "5":
            days_selected = 365
            break
        elif choice == "6":
            raw_days = get_input("Enter duration in days", default="30")
            try:
                days_selected = int(raw_days)
                if days_selected <= 0:
                    raise ValueError
                break
            except ValueError:
                print(f"{Style.RED}Please enter a positive whole number.{Style.RESET}")
        elif choice == "7":
            raw_date = get_input("Enter expiration date (YYYY-MM-DD)")
            try:
                if len(raw_date) == 10:
                    raw_date += "T23:59:59Z"
                expires_dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                if expires_dt <= datetime.now(timezone.utc):
                    print(f"{Style.RED}Expiration date must be in the future.{Style.RESET}")
                    continue
                break
            except ValueError:
                print(f"{Style.RED}Invalid format. Use YYYY-MM-DD.{Style.RESET}")
        else:
            print(f"{Style.RED}Invalid selection. Choose 1 through 7.{Style.RESET}")

    slug = slugify(customer)
    default_filename = f"{slug}_{datetime.now().strftime('%Y%m%d')}.license"
    default_out = str(OUTPUT_DIR / default_filename)

    print(f"\n{t['accent']}Step 3: Storage Location{Style.RESET}")
    out_path_str = get_input("Save license file to", default=default_out)
    out_path = Path(out_path_str)

    sync_app = False
    if PARENT_APP_DIR.is_dir() and (PARENT_APP_DIR / "src").exists():
        sync_prompt = get_input("Also copy directly to app root as '.license'? (yes/no)", default="yes")
        sync_app = sync_prompt.lower() in ("yes", "y")

    success, msg, payload = issue_license_token(
        customer=customer,
        priv_key_path=DEFAULT_PRIV_KEY,
        output_path=out_path,
        days=days_selected,
        expires_at=expires_dt,
        sync_to_app=sync_app,
    )

    if not success:
        print(f"\n{Style.BADGE_ERR} ERROR {Style.RESET} {msg}")
        pause()
        return

    # Verify immediately
    valid, _, _ = inspect_license_file(out_path, DEFAULT_PUB_KEY)

    print(f"\n{Style.BADGE_OK} SUCCESS: LICENSE TOKEN ISSUED SUCCESSFULLY {Style.RESET}")
    print(f"  {Style.BOLD}Client Name:{Style.RESET}       {t['accent']}{payload['customer']}{Style.RESET}")
    print(f"  {Style.BOLD}License ID:{Style.RESET}        {payload['license_id']}")
    print(f"  {Style.BOLD}Issued At:{Style.RESET}         {payload['issued_at']}")
    print(f"  {Style.BOLD}Expires At:{Style.RESET}        {t['accent']}{payload['expires_at']}{Style.RESET}")
    print(f"  {Style.BOLD}Saved Token:{Style.RESET}       {out_path.resolve()}")
    if sync_app:
        print(f"  {Style.BOLD}Synced to App:{Style.RESET}     {PARENT_APP_LICENSE.resolve()}")
    print(f"  {Style.BOLD}Cryptographic Sig:{Style.RESET} {Style.BADGE_OK} VALID (Ed25519) {Style.RESET}")

    print(f"\n{t['primary']}{Style.BOLD}📋 Deployment Instructions for Client Host:{Style.RESET}")
    print(f"  1. Send ONLY the file {t['accent']}{out_path.name}{Style.RESET} to the client.")
    print(f"  2. On the client host machine, rename/save it in the project root as {t['accent']}.license{Style.RESET}")
    print(f"  3. NEVER send or share {Style.BADGE_ERR} developer_private_key.pem {Style.RESET}!")
    pause()


def wizard_inspect_license() -> None:
    """Interactive wizard to inspect and verify any license file."""
    t = get_current_theme()
    clear_screen()
    print_banner("Inspect & Cryptographically Verify License")

    suggested_lic = str(PARENT_APP_LICENSE) if PARENT_APP_LICENSE.is_file() else ""
    if not suggested_lic and OUTPUT_DIR.is_dir():
        files = sorted(OUTPUT_DIR.glob("*.license"), key=os.path.getmtime, reverse=True)
        if files:
            suggested_lic = str(files[0])

    lic_path_str = get_input("License file path", default=suggested_lic or "output/sample.license")
    lic_path = Path(lic_path_str)

    pub_path_str = get_input("Public key path", default=str(DEFAULT_PUB_KEY))
    pub_path = Path(pub_path_str)

    valid, msg, payload = inspect_license_file(lic_path, pub_path)

    print("\n" + "─" * 72)
    if not valid:
        print(f"{Style.BADGE_ERR} VERIFICATION FAILED {Style.RESET} {msg}")
    else:
        rem = payload["_remaining_seconds"]
        is_expired = payload["_is_expired"]
        status_badge = f"{Style.BADGE_ERR} EXPIRED {Style.RESET}" if is_expired else f"{Style.BADGE_OK} ACTIVE & AUTHORIZED {Style.RESET}"

        print(f"{Style.BOLD}License Status:{Style.RESET}         {status_badge}")
        print(f"{Style.BOLD}Customer / Client:{Style.RESET}      {t['accent']}{payload.get('customer')}{Style.RESET}")
        print(f"{Style.BOLD}License UUID:{Style.RESET}           {payload.get('license_id', 'N/A')}")
        print(f"{Style.BOLD}Version:{Style.RESET}                {payload.get('version')}")
        print(f"{Style.BOLD}Issued Timestamp:{Style.RESET}       {payload.get('issued_at')}")
        print(f"{Style.BOLD}Expiration Date:{Style.RESET}        {t['accent']}{payload.get('expires_at')}{Style.RESET}")
        print(f"{Style.BOLD}Cryptographic Sig:{Style.RESET}      {Style.BADGE_OK} VALID (Ed25519) {Style.RESET}")

        if is_expired:
            print(f"{Style.BOLD}Time Elapsed:{Style.RESET}           {Style.RED}{abs(rem) / 86400:.2f} days ago{Style.RESET}")
            print(f"\n{Style.BADGE_ERR} WARNING {Style.RESET} Expired token: The attendance application will refuse to start.")
        else:
            print(f"{Style.BOLD}Remaining Duration:{Style.RESET}     {t['primary']}{rem / 86400:.2f} days (~{rem / 3600:.1f} hours){Style.RESET}")
            print(f"\n{Style.BADGE_OK} AUTHORIZED {Style.RESET} This license is valid, active, and cryptographically verified.")

    print("─" * 72)
    pause()


def wizard_generate_keys() -> None:
    """Interactive wizard to generate or rotate the Ed25519 developer keypair."""
    t = get_current_theme()
    clear_screen()
    print_banner("Generate or Rotate Developer Keypair")

    print(f"\n{Style.BOLD}About Key Management:{Style.RESET}")
    print(" • The Developer Private Key is stored inside this license_kit.")
    print("   Keep it strictly private. Never transfer it to client hosts.")
    print(" • The Public Key is embedded into the client application.")
    print("   The client application uses it to verify tokens, but cannot forge them.")

    if DEFAULT_PRIV_KEY.is_file():
        print(f"\n{Style.BADGE_WARN} WARNING {Style.RESET} {Style.BOLD}A private key already exists in this kit!{Style.RESET}")
        print(f"Path: {DEFAULT_PRIV_KEY.resolve()}")
        print("Rotating keys will invalidate any previously issued licenses that rely on the old public key.")
        confirm = get_input("Overwrite and generate a new keypair? (yes/no)", default="no")
        if confirm.lower() not in ("yes", "y"):
            print(f"{t['accent']}Cancelled.{Style.RESET}")
            pause()
            return

    sync_app = PARENT_APP_PUB_KEY.parent.exists()
    success, msg = generate_keypair(DEFAULT_PRIV_KEY, DEFAULT_PUB_KEY, force=True, sync_to_app=sync_app)

    if success:
        print(f"\n{Style.BADGE_OK} SUCCESS: New Ed25519 Keypair Generated! {Style.RESET}")
        print(f"  [Private Key - Secret] {DEFAULT_PRIV_KEY.resolve()}")
        print(f"  [Public Key  - Export] {DEFAULT_PUB_KEY.resolve()}")
        if sync_app:
            print(f"  [Synced to App Public Key] {PARENT_APP_PUB_KEY.resolve()}")
    else:
        print(f"\n{Style.BADGE_ERR} ERROR {Style.RESET} {msg}")

    pause()


def wizard_theme_selection() -> None:
    """Interactive wizard to change font colors and background styles."""
    clear_screen()
    print_banner("Customize Terminal Font & Background Theme")

    current = get_current_theme()
    print(f"\n{Style.BOLD}Current Active Theme:{Style.RESET} {current['accent']}{current['name']}{Style.RESET}")
    print(f"\n{Style.BOLD}SELECT A FONT & BACKGROUND PALETTE:{Style.RESET}\n")

    theme_keys = list(THEMES.keys())
    for idx, key in enumerate(theme_keys, start=1):
        th = THEMES[key]
        preview_badge = f"{th['key_tag']} {idx} {Style.RESET}"
        preview_banner = f"{th['banner_bg']}{th['banner_fg']}  {th['name']}  {Style.RESET}"
        print(f"  {preview_badge}  {preview_banner}")

    print()
    choice = get_input("Choose palette number [1-5]", default="1")
    try:
        idx_choice = int(choice)
        if 1 <= idx_choice <= len(theme_keys):
            selected_key = theme_keys[idx_choice - 1]
            save_theme(selected_key)
            new_theme = get_current_theme()
            print(f"\n{Style.BADGE_OK} THEME APPLIED {Style.RESET} Switched to {new_theme['accent']}{new_theme['name']}{Style.RESET}")
        else:
            print(f"{Style.RED}Invalid choice.{Style.RESET}")
    except ValueError:
        print(f"{Style.RED}Please enter a number between 1 and 5.{Style.RESET}")

    pause()


def show_security_guide() -> None:
    """Display comprehensive security and deployment guide."""
    t = get_current_theme()
    clear_screen()
    print_banner("Security Architecture & Operator Guide")

    guide_text = f"""
{t['accent']}{Style.BOLD}1. WHY THIS KIT IS SEPARATE{Style.RESET}
────────────────────────────────────────────────────────────────────────
• {Style.BOLD}Absolute Key Isolation:{Style.RESET}
  This 'license_kit/' directory contains your private signing key
  ('developer_private_key.pem'). You can keep this folder on your personal
  laptop or an encrypted USB drive, completely separate from the project code.
  Even if someone gains full root/admin access to the host machine, they
  will NEVER have the private key required to generate licenses.

• {Style.BOLD}Zero File Deletion / Ethical Compliance:{Style.RESET}
  The attendance system enforces expiration cleanly through a {Style.BOLD}Hard Boot Exit{Style.RESET}
  (terminating with sys.exit(1)) and HTTP 403 Forbidden for in-flight requests.
  It NEVER executes destructive file deletion routines or logic bombs.

{t['accent']}{Style.BOLD}2. HOW TO DELIVER TO A CLIENT HOST{Style.RESET}
────────────────────────────────────────────────────────────────────────
  {Style.BOLD}Step 1:{Style.RESET} On your workstation, run Option 1 to issue a license.
  {Style.BOLD}Step 2:{Style.RESET} Grab the generated file from 'license_kit/output/'.
  {Style.BOLD}Step 3:{Style.RESET} Send ONLY that single file to the client.
  {Style.BOLD}Step 4:{Style.RESET} Place it on the host machine as '.license' in the app root.
  {Style.BOLD}Step 5:{Style.RESET} The application boots, verifies the signature, and runs!

{t['accent']}{Style.BOLD}3. RENEWING AN EXPIRED CLIENT{Style.RESET}
────────────────────────────────────────────────────────────────────────
When a client pays their renewal or milestone:
  1. Open this console (Option 1).
  2. Issue a new license with the extended expiration date.
  3. Send the new '.license' file to the client to overwrite their old one.
  4. The system immediately resumes operation without needing code changes!
"""
    print(guide_text)
    pause()


def show_diagnostics() -> None:
    """Display in-depth diagnostics of all cryptographic keys."""
    t = get_current_theme()
    clear_screen()
    print_banner("System Diagnostics & File Integrity")

    print(f"\n{Style.BOLD}Kit Directory Inspection:{Style.RESET}")
    items = [
        ("Kit Private Key (Secret)", DEFAULT_PRIV_KEY),
        ("Kit Public Key (Verifier)", DEFAULT_PUB_KEY),
    ]
    if PARENT_APP_DIR.is_dir():
        items.extend([
            ("Parent App Public Key", PARENT_APP_PUB_KEY),
            ("Parent App Active License", PARENT_APP_LICENSE),
            ("Parent App Anti-Rollback State", PARENT_APP_STATE),
        ])

    for label, path in items:
        if path.is_file():
            sz = path.stat().st_size
            mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            mode = oct(path.stat().st_mode & 0o777)
            print(f"  {Style.BADGE_OK} FOUND {Style.RESET} {Style.BOLD}{label:<28}{Style.RESET} : {path} {Style.DIM}({sz} bytes, {mode}, modified: {mtime}){Style.RESET}")
        else:
            print(f"  {Style.BADGE_ERR} MISSING {Style.RESET} {Style.BOLD}{label:<28}{Style.RESET} : {Style.RED}NOT FOUND{Style.RESET} ({path})")

    # List output licenses
    if OUTPUT_DIR.is_dir():
        tokens = list(OUTPUT_DIR.glob("*.license"))
        print(f"\n{Style.BOLD}Issued Licenses in output/ ({len(tokens)} files):{Style.RESET}")
        for t_file in sorted(tokens, key=os.path.getmtime, reverse=True)[:5]:
            sz = t_file.stat().st_size
            print(f"   • {t['accent']}{t_file.name}{Style.RESET} ({sz} bytes)")

    pause()


# =============================================================================
# Main Loop & Entry Points
# =============================================================================

def interactive_terminal_app() -> int:
    """Main interactive terminal application loop."""
    load_theme()
    while True:
        t = get_current_theme()
        clear_screen()
        print_banner()
        render_dashboard()

        print(f"\n{t['accent']}\033[1mAVAILABLE ACTIONS:{Style.RESET}")
        print(f"  {t['key_tag']} 1 {Style.RESET} {Style.BOLD_WHITE}Issue Client License Token{Style.RESET}        {Style.DIM}(Interactive Wizard){Style.RESET}")
        print(f"  {t['key_tag']} 2 {Style.RESET} {Style.BOLD_WHITE}Inspect / Verify License File{Style.RESET}     {Style.DIM}(Signature & Expiry Check){Style.RESET}")
        print(f"  {t['key_tag']} 3 {Style.RESET} {Style.BOLD_WHITE}Generate / Rotate Keypair{Style.RESET}         {Style.DIM}(Ed25519 Private & Public Keys){Style.RESET}")
        print(f"  {t['key_tag']} 4 {Style.RESET} {Style.BOLD_WHITE}Change Terminal Theme & Colors{Style.RESET}    {Style.DIM}(Font & Background Palette){Style.RESET}")
        print(f"  {t['key_tag']} 5 {Style.RESET} {Style.BOLD_WHITE}Security & Deployment Guide{Style.RESET}       {Style.DIM}(Architecture & Best Practices){Style.RESET}")
        print(f"  {t['key_tag']} 6 {Style.RESET} {Style.BOLD_WHITE}System Diagnostics{Style.RESET}               {Style.DIM}(Inspect Keys & Tokens){Style.RESET}")
        print(f"  {Style.DIM}[ 0 ] Exit{Style.RESET}")

        try:
            choice = get_input("\nEnter choice", default="1")
        except (KeyboardInterrupt, EOFError):
            print(f"\n{t['primary']}Exiting console. Goodbye!{Style.RESET}")
            return 0

        if choice == "1":
            wizard_issue_license()
        elif choice == "2":
            wizard_inspect_license()
        elif choice == "3":
            wizard_generate_keys()
        elif choice == "4":
            wizard_theme_selection()
        elif choice == "5":
            show_security_guide()
        elif choice == "6":
            show_diagnostics()
        elif choice in ("0", "exit", "quit", "q"):
            print(f"\n{t['primary']}Exiting console. Goodbye!{Style.RESET}")
            return 0
        else:
            print(f"{Style.RED}Invalid option '{choice}'. Choose 0 through 6.{Style.RESET}")
            time.sleep(1)


def main() -> None:
    # If invoked with no arguments or explicitly 'ui', launch Terminal UI
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1].lower() in ("ui", "interactive", "console", "tui")):
        sys.exit(interactive_terminal_app())

    parser = argparse.ArgumentParser(description="Standalone Developer License Kit CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ui subcommand
    p_ui = subparsers.add_parser("ui", help="Launch Interactive Terminal UI Console")
    p_ui.set_defaults(func=lambda args: interactive_terminal_app())

    # generate-keys
    p_gen = subparsers.add_parser("generate-keys", help="Generate developer Ed25519 keypair")
    p_gen.add_argument("--priv-out", default=str(DEFAULT_PRIV_KEY), help="Path to save private key")
    p_gen.add_argument("--pub-out", default=str(DEFAULT_PUB_KEY), help="Path to save public key")
    p_gen.add_argument("--force", action="store_true", help="Overwrite existing private key")
    p_gen.set_defaults(func=lambda a: generate_keypair(Path(a.priv_out), Path(a.pub_out), force=a.force)[0])

    # issue
    p_issue = subparsers.add_parser("issue", aliases=["issue-license"], help="Issue a signed license file")
    p_issue.add_argument("--customer", required=True, help="Customer or organization name")
    p_issue.add_argument("--days", type=int, default=30, help="Duration in days (default: 30)")
    p_issue.add_argument("--output", default=str(OUTPUT_DIR / "sample.license"), help="Path to save license")
    p_issue.add_argument("--priv-key", default=str(DEFAULT_PRIV_KEY), help="Developer private key path")
    p_issue.set_defaults(func=lambda a: issue_license_token(a.customer, Path(a.priv_key), Path(a.output), days=a.days)[0])

    # inspect
    p_inspect = subparsers.add_parser("inspect", aliases=["inspect-license"], help="Verify and inspect a license")
    p_inspect.add_argument("--license", required=True, help="Path to license file")
    p_inspect.add_argument("--pub-key", default=str(DEFAULT_PUB_KEY), help="Path to public key")
    p_inspect.set_defaults(func=lambda a: inspect_license_file(Path(a.license), Path(a.pub_key))[0])

    args = parser.parse_args()
    sys.exit(0 if args.func(args) else 1)


if __name__ == "__main__":
    main()
