# VTOP Facility Registration Assistant

An automated assistant for VTOP Physical Education facility registrations with human-in-the-loop verification, persistent browser sessions, fast-path AJAX navigation, and configurable facility presets.

---

## Supported Facility Presets

The following facilities from the Physical Education Registration portal are pre-configured:

| # | Facility Name |
| :---: | :--- |
| **1** | Swimming Men |
| **2** | Karate Men |
| **3** | A/C Squash Men |
| **4** | Badminton Indoor Men |
| **5** | Synthetic Tennis Men |
| **6** | A/C Snooker Men |
| **7** | Indoor A/C Gymnasium Men |
| **8** | Fitty A/C Gymnasium Men |
| **9** | Fitty STAG A/C Gymnasium Men |
| **10** | Trendset A/C Gymnasium - Men |

You can also enter any custom facility name (case-insensitive substring match).

---

## Project Structure

```
vtop-sniper/
├── vtop_sniper.py                   # Playwright automation script (Python / Firefox)
├── vtop_facility_registration.user.js # Userscript (Violentmonkey / Tampermonkey)
├── .env.example                     # Template for credentials and default facility
├── requirements.txt                 # Python dependencies
├── .gitignore                       # Prevents committing secrets or browser cache
└── README.md
```

---

## Option 1: Python Playwright Assistant

### Setup

1. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install firefox
   ```

3. **Configure your credentials:**
   ```bash
   cp .env.example .env
   chmod 600 .env
   ```
   Edit `.env` with your registration number, password, and default facility:
   ```ini
   VTOP_USERNAME=YOUR_REG_NUMBER
   VTOP_PASSWORD=YOUR_PASSWORD
   TARGET_FACILITY=Swimming Men
   ```

### Running the Script

1. **Interactive Menu Mode (Default):**
   ```bash
   python3 vtop_sniper.py
   ```
   A numbered menu will appear:
   ```text
   ============================================================
     SELECT TARGET FACILITY:
   ============================================================
     [ 1] Swimming Men (Default)
     [ 2] Karate Men
     [ 3] A/C Squash Men
     [ 4] Badminton Indoor Men
     [ 5] Synthetic Tennis Men
     [ 6] A/C Snooker Men
     [ 7] Indoor A/C Gymnasium Men
     [ 8] Fitty A/C Gymnasium Men
     [ 9] Fitty STAG A/C Gymnasium Men
     [10] Trendset A/C Gymnasium - Men
     [11] Custom (type your own)
   ============================================================
   Enter choice [1-11] or press Enter for 'Swimming Men':
   ```
   - Press **Enter** to proceed immediately with your `.env` default.
   - Or type a number (`1` - `10`) to select another facility.

2. **Command Line Flag Mode:**
   Bypass the prompt and launch directly with your chosen target:
   ```bash
   python3 vtop_sniper.py -f "Badminton Indoor Men"
   python3 vtop_sniper.py -f "Synthetic Tennis Men"
   ```

3. **Non-Interactive Mode:**
   ```bash
   python3 vtop_sniper.py --non-interactive
   ```

### Workflow
1. Firefox launches using a persistent profile (`./firefox_profile`).
2. The script navigates directly to `https://vtop.vit.ac.in/vtop/login`, pre-fills your username and password, and places the cursor into the CAPTCHA box.
3. Solve any verification challenge and click **Submit**.
4. The moment `/vtop/content` loads, the script triggers the fast-path in-DOM AJAX handler for **Facility Registration**, overrides confirmation dialogs, and monitors for your chosen facility.
5. If seats become available, it clicks **Register** immediately.
6. Press **Alt + R** in Firefox at any time to force a manual re-scan.

---

## Option 2: Browser Userscript (Violentmonkey / Tampermonkey)

If you prefer running directly in your regular Firefox browser without running Python:

1. Install the [Violentmonkey](https://violentmonkey.github.io/) extension in Firefox.
2. Open the Violentmonkey dashboard and click **New script (+)**.
3. Paste the contents of [`vtop_facility_registration.user.js`](vtop_facility_registration.user.js) and save.
4. Navigate to `https://vtop.vit.ac.in/vtop/login`.
   - On first run, it will prompt you once to save your login ID and password in extension storage.
5. Once logged in, a floating status badge will appear at the bottom-right of `/vtop/content` with an interactive dropdown allowing you to switch facilities on the fly.
6. Press **Alt + R** to trigger immediate re-registration.

---

## Security & Privacy Notice

- Never commit your `.env` file or `./firefox_profile/` directory. Both are included in `.gitignore` by default.
- Per security and anti-bot policies, CAPTCHA and human-verification challenges must be solved manually.
