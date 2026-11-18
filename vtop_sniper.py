#!/usr/bin/env python3
"""
VTOP Facility Registration Assistant (Human-in-the-Loop)
Browser: Firefox (Persistent Profile in Headed Mode via Playwright)
"""

import os
import re
import sys
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, Dialog

# Base paths
BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / "firefox_profile"

# Load environment configuration
load_dotenv(BASE_DIR / ".env")

LOGIN_URL = "https://vtop.vit.ac.in/vtop/login"
DASHBOARD_URL_PATTERN = "**/vtop/content**"


# Known facility presets from VTOP Physical Education Registration
FACILITY_PRESETS = [
    "Swimming Men",
    "Karate Men",
    "A/C Squash Men",
    "Badminton Indoor Men",
    "Synthetic Tennis Men",
    "A/C Snooker Men",
    "Indoor A/C Gymnasium Men",
    "Fitty A/C Gymnasium Men",
    "Fitty STAG A/C Gymnasium Men",
    "Trendset A/C Gymnasium - Men",
]


def parse_arguments():
    """Parse command line arguments for quick overrides."""
    parser = argparse.ArgumentParser(
        description="VTOP Facility Registration Assistant with Human-in-the-Loop authentication."
    )
    parser.add_argument(
        "-f",
        "--facility",
        type=str,
        default=None,
        help="Target facility name to register (e.g. 'Swimming Men', 'Karate Men'). Overrides menu selection.",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=300,
        help="Monitoring loop duration in seconds. Default: 300 (5 minutes)",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip terminal selection menu and use default from .env or 'Swimming Men'.",
    )
    return parser.parse_args()


def choose_facility_interactive(cli_override: str | None, non_interactive: bool) -> str:
    """Provides an interactive terminal menu to select a facility preset."""
    # 1. If explicit command line argument was passed, use it directly
    if cli_override:
        return cli_override

    env_default = os.getenv("TARGET_FACILITY", "Swimming Men")

    # 2. If non-interactive mode is requested, use environment default
    if non_interactive or not sys.stdin.isatty():
        return env_default

    # 3. Interactive terminal menu
    print("\n" + "=" * 60)
    print("  SELECT TARGET FACILITY:")
    print("=" * 60)
    for idx, name in enumerate(FACILITY_PRESETS, start=1):
        marker = " (Default)" if name.lower() == env_default.lower() else ""
        print(f"  [{idx:2d}] {name}{marker}")
    print(f"  [{len(FACILITY_PRESETS) + 1:2d}] Custom (type your own)")
    print("=" * 60)

    try:
        choice = input(f"Enter choice [1-{len(FACILITY_PRESETS) + 1}] or press Enter for '{env_default}': ").strip()
        if not choice:
            return env_default
        
        if choice.isdigit():
            c_int = int(choice)
            if 1 <= c_int <= len(FACILITY_PRESETS):
                return FACILITY_PRESETS[c_int - 1]
            elif c_int == len(FACILITY_PRESETS) + 1:
                custom_name = input("Enter custom facility name (case-insensitive substring match): ").strip()
                return custom_name if custom_name else env_default

        # If user typed the name directly
        return choice
    except (EOFError, KeyboardInterrupt):
        print(f"\n[INFO] Using default: {env_default}")
        return env_default


def prefill_credentials_and_wait_for_login(page: Page, username: str, password: str):
    """
    Navigates to /vtop/login.
    If the role selection landing page (#stdForm) is displayed, directly triggers
    submitForm('stdForm') and waits for the login form to render.
    Then pre-fills username & password and focuses cursor into the CAPTCHA field.
    """
    print(f"[INFO] Navigating to {LOGIN_URL}...")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")

    # Adaptive Step: If role selection landing page is shown, submit Student form directly
    try:
        if page.locator("#stdForm").is_visible(timeout=2500):
            print("[INFO] Role selection landing page detected. Submitting Student form...")
            submitted = page.evaluate(
                """
                () => {
                    if (typeof submitForm === 'function') {
                        submitForm('stdForm');
                        return true;
                    }
                    const aTag = document.querySelector("#stdForm a[onclick*='submitForm'], #stdForm a");
                    if (aTag) {
                        aTag.click();
                        return true;
                    }
                    return false;
                }
                """
            )
            if not submitted:
                page.locator("#stdForm a[onclick*='submitForm'], #stdForm a").first.click()

            # Wait specifically for the login form's username field to render
            page.locator("#vtopLoginForm, input[name='username'], #username").first.wait_for(state="visible", timeout=6000)
            print("[INFO] Student login form loaded.")
    except Exception:
        # Already directly on login form
        pass

    # Locate username and password fields directly
    user_locator = page.locator("#username, input[name='username'], input[name='uname'], #uname").first
    user_locator.wait_for(state="visible", timeout=15000)

    pwd_locator = page.locator("#password, input[name='password'], input[type='password']").first
    pwd_locator.wait_for(state="visible", timeout=15000)

    # Locate CAPTCHA text box
    captcha_locator = page.locator("#captchaStr, input[name='captchaStr'], input[name='captchaCheck'], input[name*='captcha' i]").first

    if not username or not password or username == "YOUR_REG_NUMBER":
        print("[WARNING] Credentials not configured in .env! Please enter them manually in the browser.")
    else:
        print("[INFO] Pre-filling credentials...")
        user_locator.fill(username)
        pwd_locator.fill(password)

    if captcha_locator.count() > 0:
        print("[INFO] Focusing cursor into the CAPTCHA field...")
        captcha_locator.focus()

    print("\n" + "=" * 60)
    print(">>> MANUAL STEP REQUIRED <<<")
    print("1. Complete any verification/CAPTCHA shown in Firefox.")
    print("2. Click 'Submit' (or press Enter).")
    print("Waiting for dashboard redirect to /vtop/content...")
    print("=" * 60 + "\n")

    # 1. Locate the CAPTCHA input box
    captcha_input = page.locator("#captchaStr")

    # 2. Get the bounding box coordinates of the input element to move the mouse pointer there
    box = captcha_input.bounding_box()
    if box:
        # Move the mouse pointer smoothly to the center of the CAPTCHA box
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        print("[INFO] Mouse pointer placed inside the CAPTCHA input box.")

    # Focus the element explicitly
    captcha_input.focus()

    print("[INFO] Waiting for CAPTCHA input...")

    # 3. Polling loop to check when you finish typing (6 characters)
    while True:
        captcha_value = captcha_input.input_value().strip()
        
        # Once 6 characters are typed, press Enter
        if len(captcha_value) == 6:
            print(f"[INFO] CAPTCHA detected ({captcha_value}). Pressing Enter...")
            
            # Press the Enter key to submit the form
            captcha_input.press("Enter")
            break
                
        time.sleep(0.1)  # Check every 100ms

    # Wait for successful login redirect
    page.wait_for_url("**/vtop/content", timeout=1000000)

    # Wait for the user to submit and land on the dashboard
    page.wait_for_url(DASHBOARD_URL_PATTERN, timeout=0)
    print("[SUCCESS] Logged in successfully! Dashboard loaded.")


def inject_dialog_handler_and_hotkeys(page: Page):
    """Sets up auto-accepting native confirmation dialogs and in-browser Alt+R hotkey."""
    def handle_dialog(dialog: Dialog):
        print(f"[DIALOG] Auto-accepting browser dialog: '{dialog.message}' (type: {dialog.type})")
        dialog.accept()

    page.on("dialog", handle_dialog)

    page.evaluate(
        """
        () => {
            window.confirm = () => true;
            window.alert = () => true;

            window.addEventListener('keydown', (e) => {
                if (e.altKey && (e.key === 'r' || e.key === 'R' || e.code === 'KeyR')) {
                    e.preventDefault();
                    console.log('[VTOP SNIPER] Alt+R triggered!');
                    window.dispatchEvent(new CustomEvent('vtop-sniper-retry'));
                }
            });
            console.log('[VTOP SNIPER] Dialog overrides and Alt+R shortcut initialized.');
        }
        """
    )


def ensure_facility_registration_page(page: Page) -> bool:
    """
    Checks if we are on the Facility Registration page.
    If not, navigates by directly triggering the underlying AJAX request/onclick handler
    bypassing menu hover/animation delays, with fallback to UI navigation.
    Returns True if the facility registration page/table is present.
    """
    is_already_open = page.evaluate(
        """
        () => {
            const text = document.body.innerText || '';
            return text.includes('Physical Education') || 
                   (text.includes('Facility Registration') && (text.includes('Swimming') || text.includes('Register')));
        }
        """
    )
    if is_already_open:
        return True

    # Priority 1: Direct in-DOM AJAX invocation (Bypasses UI hover/open animations)
    triggered = page.evaluate(
        """
        () => {
            const allElements = Array.from(document.querySelectorAll('a, li, button, span'));
            const fac = allElements.find(el => {
                const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                return txt.includes('facility registration');
            });

            if (fac) {
                // If the link has an inline onclick (e.g. processMenu(...)), invoke it directly
                const onclickAttr = fac.getAttribute('onclick');
                if (onclickAttr) {
                    try {
                        new Function(onclickAttr).call(fac);
                        return 'onclick_invoked';
                    } catch (e) {
                        // Fall back to synthetic click
                    }
                }
                fac.click();
                return 'direct_click';
            }
            return null;
        }
        """
    )

    if triggered:
        print(f"[FAST-PATH] Direct AJAX triggered ({triggered}). Waiting for fragment...")
        page.wait_for_timeout(400)
        return True

    # Priority 2: Fallback to expanding 'Services' dropdown via UI
    print("[FALLBACK] Direct AJAX element not found yet. Expanding 'Services' menu...")
    try:
        services_link = page.locator("a, li, span, button", has_text=re.compile(r"^Services$|▾\s*Services|Services\s*▾", re.I)).first
        if not services_link.is_visible(timeout=1000):
            services_link = page.locator("a:has-text('Services'), li:has-text('Services')").first
        
        if services_link.is_visible(timeout=1500):
            services_link.click()
            page.wait_for_timeout(250)

        facility_link = page.locator("a, li, button, span", has_text=re.compile(r"Facility\s*Registration", re.I)).first
        if facility_link.is_visible(timeout=1500):
            facility_link.click()
            page.wait_for_timeout(400)
            return True
    except Exception:
        pass

    return False


def find_and_click_target_facility(page: Page, target_name: str) -> bool:
    """
    Scans the table for TARGET_FACILITY and clicks the Register button.
    Returns True if successfully clicked, False otherwise.
    """
    target_regex = re.compile(rf"{re.escape(target_name)}", re.IGNORECASE)

    facility_row = page.locator("tr", has_text=target_regex)
    if facility_row.count() == 0:
        return False

    print(f"[FOUND] Found table row for '{target_name}'!")
    register_btn = facility_row.first.locator(
        "button:has-text('Register'), input[type='button'][value*='Register' i], a:has-text('Register'), .btn:has-text('Register')"
    ).first

    if register_btn.count() > 0 and register_btn.is_visible():
        if register_btn.is_enabled():
            print(f"[ACTION] Clicking Register button for '{target_name}'!")
            register_btn.click()
            return True
        else:
            print(f"[WAIT] Found '{target_name}', but Register button is disabled (seats 0 or registration closed).")
            return False
    else:
        print(f"[WAIT] Found '{target_name}' row, but Register button not rendered yet.")
        return False


def run():
    args = parse_arguments()
    target_facility = choose_facility_interactive(args.facility, args.non_interactive)
    timeout_seconds = args.timeout

    username = os.getenv("VTOP_USERNAME", "")
    password = os.getenv("VTOP_PASSWORD", "")

    print("\n" + "=" * 60)
    print("  VTOP Facility Registration Assistant")
    print(f"  Target Facility: {target_facility}")
    print(f"  Persistent Profile: {PROFILE_DIR}")
    print("=" * 60)

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        # Launch persistent Firefox profile to retain extensions and cookies
        context = p.firefox.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            ignore_https_errors=True,
            firefox_user_prefs={
                "security.pki.sha1_enforcement_level": 0,
                "security.ssl.enable_ocsp_stapling": False,
                "dom.webnotifications.enabled": False,
                "browser.download.folderList": 2,
            },
            viewport={"width": 1366, "height": 768},
        )
        page = context.pages[0] if context.pages else context.new_page()

        # Step 1: Pre-fill credentials and wait for human login
        prefill_credentials_and_wait_for_login(page, username, password)

        # Step 2: Set up dialog handler and keyboard shortcuts
        inject_dialog_handler_and_hotkeys(page)

        # Step 3: Wait for dashboard to finish initial network calls
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1000)

        # Step 4: Active Monitoring & Registration Loop
        print(f"\n[INFO] Actively monitoring for Facility Registration & '{target_facility}'...")
        registered = False
        start_time = time.time()
        last_nav_attempt = 0

        while time.time() - start_time < timeout_seconds and not registered:
            current_time = time.time()

            # Re-attempt navigation to Facility Registration every 2.5s if still on dashboard
            if current_time - last_nav_attempt > 2.5:
                ensure_facility_registration_page(page)
                last_nav_attempt = current_time

            # Attempt to locate target facility and click Register
            registered = find_and_click_target_facility(page, target_facility)
            if registered:
                print("\n[SUCCESS] Registration action submitted!")
                print("[INFO] Please review the browser window to confirm final status.")
                break

            time.sleep(0.4)

        print("\n[INFO] Script will remain open. Press Alt+R in the browser to re-trigger, or press Ctrl+C in terminal to exit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[INFO] Exiting...")
        finally:
            context.close()


if __name__ == "__main__":
    run()
