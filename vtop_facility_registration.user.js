// ==UserScript==
// @name         VTOP Facility Registration Assistant (Human-in-the-Loop)
// @namespace    https://vtop.vit.ac.in/
// @version      1.3
// @description  Automates post-login navigation to Facility Registration and snipes selected facility on VTOP with manual CAPTCHA entry.
// @author       VTOP Assistant
// @match        https://vtop.vit.ac.in/vtop/*
// @grant        GM_setValue
// @grant        GM_getValue
// @run-at       document-idle
// ==/UserScript==

(function () {
    'use strict';

    // ==========================================================================
    // CONFIGURATION: PRESET YOUR SETTINGS HERE
    // ==========================================================================

    // Known facility options from VTOP Physical Education Registration
    const FACILITY_PRESETS = [
        "Swimming Men",
        "Karate Men",
        "A/C Squash Men",
        "Badminton Indoor Men",
        "Synthetic Tennis Men",
        "A/C Snooker Men",
        "Indoor A/C Gymnasium Men",
        "Fitty A/C Gymnasium Men",
        "Fitty STAG A/C Gymnasium Men",
        "Trendset A/C Gymnasium - Men"
    ];

    // Default target facility (can be changed on the fly via the badge dropdown)
    let TARGET_FACILITY = GM_getValue("TARGET_FACILITY", "Swimming Men");

    // Preset your credentials (optional):
    // Leave them empty ("") to be prompted once on first load (saved safely in browser extension storage)
    const PRESET_USERNAME = ""; 
    const PRESET_PASSWORD = "";

    const DEFAULT_USERNAME = PRESET_USERNAME || GM_getValue("VTOP_USERNAME", "");
    const DEFAULT_PASSWORD = PRESET_PASSWORD || GM_getValue("VTOP_PASSWORD", "");

    // Auto-override native confirmation and alert dialogs
    try {
        window.confirm = () => true;
        window.alert = () => true;
        if (typeof unsafeWindow !== 'undefined') {
            unsafeWindow.confirm = () => true;
            unsafeWindow.alert = () => true;
        }
    } catch (e) {
        console.warn("[VTOP Assistant] Dialog override error:", e);
    }

    // Floating status badge with Interactive Facility Dropdown
    function createStatusBadge() {
        if (document.getElementById("vtop-sniper-badge")) return;
        const badge = document.createElement("div");
        badge.id = "vtop-sniper-badge";
        badge.style.position = "fixed";
        badge.style.bottom = "20px";
        badge.style.right = "20px";
        badge.style.padding = "12px 18px";
        badge.style.backgroundColor = "#1a1a2e";
        badge.style.color = "#00ffcc";
        badge.style.fontFamily = "system-ui, -apple-system, sans-serif";
        badge.style.fontSize = "13px";
        badge.style.borderRadius = "10px";
        badge.style.boxShadow = "0 4px 16px rgba(0,0,0,0.5)";
        badge.style.zIndex = "999999";
        badge.style.border = "1px solid #00ffcc";
        badge.style.display = "flex";
        badge.style.flexDirection = "column";
        badge.style.gap = "8px";

        // Top info line
        const header = document.createElement("div");
        header.style.display = "flex";
        header.style.justifyContent = "space-between";
        header.style.alignItems = "center";
        header.innerHTML = `<strong>⚡ VTOP Assistant</strong> <span style="font-size:11px;color:#aaa;">(Alt+R)</span>`;
        badge.appendChild(header);

        // Facility selector row
        const selectorRow = document.createElement("div");
        selectorRow.style.display = "flex";
        selectorRow.style.alignItems = "center";
        selectorRow.style.gap = "6px";

        const label = document.createElement("span");
        label.innerText = "Target:";
        label.style.color = "#fff";
        label.style.fontSize = "12px";
        selectorRow.appendChild(label);

        const select = document.createElement("select");
        select.id = "vtop-facility-select";
        select.style.backgroundColor = "#0f3460";
        select.style.color = "#fff";
        select.style.border = "1px solid #e94560";
        select.style.borderRadius = "5px";
        select.style.padding = "3px 6px";
        select.style.fontSize = "12px";
        select.style.cursor = "pointer";

        FACILITY_PRESETS.forEach(f => {
            const opt = document.createElement("option");
            opt.value = f;
            opt.innerText = f;
            if (f.toLowerCase() === TARGET_FACILITY.toLowerCase()) opt.selected = true;
            select.appendChild(opt);
        });

        select.addEventListener("change", (e) => {
            TARGET_FACILITY = e.target.value;
            GM_setValue("TARGET_FACILITY", TARGET_FACILITY);
            updateStatus(`Target updated to: ${TARGET_FACILITY}`);
            scanAndRegister();
        });

        selectorRow.appendChild(select);
        badge.appendChild(selectorRow);

        // Status text line
        const statusDiv = document.createElement("div");
        statusDiv.id = "vtop-sniper-status-text";
        statusDiv.style.fontSize = "12px";
        statusDiv.style.color = "#00ffcc";
        statusDiv.innerText = `Monitoring for ${TARGET_FACILITY}...`;
        badge.appendChild(statusDiv);

        document.body.appendChild(badge);
    }

    function updateStatus(text, color = "#00ffcc") {
        const statusDiv = document.getElementById("vtop-sniper-status-text");
        if (statusDiv) {
            statusDiv.innerText = text;
            statusDiv.style.color = color;
        }
    }

    // ==========================================
    // 1. LOGIN AUTOMATION (/vtop/login)
    // ==========================================
    if (window.location.pathname.includes("/login")) {
        createStatusBadge();

        // Check if on role selection landing page
        const stdForm = document.querySelector("#stdForm");
        if (stdForm) {
            updateStatus("Role selection detected. Submitting Student form...", "#ffcc00");
            if (typeof submitForm === 'function') {
                submitForm('stdForm');
            } else {
                const aTag = stdForm.querySelector("a[onclick*='submitForm'], a");
                if (aTag) aTag.click();
            }
            return;
        }

        updateStatus("Pre-filling credentials... Please enter CAPTCHA manually.");

        let uname = DEFAULT_USERNAME;
        let passwd = DEFAULT_PASSWORD;

        if (!uname) {
            uname = prompt("[VTOP Assistant] Enter your VTOP Login ID / Username (stored locally):", "");
            if (uname) GM_setValue("VTOP_USERNAME", uname);
        }
        if (!passwd) {
            passwd = prompt("[VTOP Assistant] Enter your VTOP Password (stored locally):", "");
            if (passwd) GM_setValue("VTOP_PASSWORD", passwd);
        }

        const usernameInput = document.querySelector("#username, input[name='username'], input[name='uname'], #uname");
        const passwordInput = document.querySelector("#password, input[name='password'], input[type='password']");
        const captchaInput = document.querySelector("#captchaStr, input[name='captchaStr'], input[name='captchaCheck'], input[name*='captcha' i]");

        if (usernameInput && uname) {
            usernameInput.value = uname;
            usernameInput.dispatchEvent(new Event('input', { bubbles: true }));
        }

        if (passwordInput && passwd) {
            passwordInput.value = passwd;
            passwordInput.dispatchEvent(new Event('input', { bubbles: true }));
        }

        if (captchaInput) {
            captchaInput.focus();
        }
    }

    // ==========================================
    // 2. DASHBOARD & FACILITY AUTOMATION (/vtop/content)
    // ==========================================
    if (window.location.pathname.includes("/content")) {
        createStatusBadge();
        updateStatus(`Logged In. Opening Services -> Facility Registration...`);

        function triggerFacilityRegistration() {
            const bodyText = document.body.innerText || '';
            if (bodyText.includes('Physical Education') || (bodyText.includes('Facility Registration') && bodyText.includes('Swimming'))) {
                return true;
            }

            const allElements = Array.from(document.querySelectorAll("a, li, button, span"));

            // 1. Direct AJAX / onclick invocation (fastest path, no dropdown animation delay)
            const targetLink = allElements.find(el => {
                const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                return txt.includes("facility registration");
            });

            if (targetLink) {
                const onclickAttr = targetLink.getAttribute('onclick');
                if (onclickAttr) {
                    try {
                        new Function(onclickAttr).call(targetLink);
                        updateStatus(`Direct AJAX invoked. Monitoring for ${TARGET_FACILITY}...`);
                        return true;
                    } catch (e) {
                        // Fallback to click
                    }
                }
                targetLink.click();
                updateStatus(`Direct click dispatched. Monitoring for ${TARGET_FACILITY}...`);
                return true;
            }

            // 2. Fallback: expand Services dropdown
            const servicesLink = allElements.find(el => {
                const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                return txt === "services" || txt.includes("services");
            });

            if (servicesLink) {
                servicesLink.click();
                updateStatus("Opening Services menu...");
                setTimeout(() => {
                    const retryFac = Array.from(document.querySelectorAll("a, li, button, span")).find(el => {
                        const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                        return txt.includes("facility registration");
                    });
                    if (retryFac) retryFac.click();
                }, 250);
            }

            return false;
        }

        function scanAndRegister() {
            const rows = Array.from(document.querySelectorAll("tr"));
            const targetRow = rows.find(row => {
                const text = row.textContent || "";
                return text.toLowerCase().includes(TARGET_FACILITY.toLowerCase());
            });

            if (!targetRow) return false;

            const registerBtn = targetRow.querySelector("button, input[type='button'], a, .btn");
            if (registerBtn && registerBtn.textContent.toLowerCase().includes("register")) {
                if (!registerBtn.disabled) {
                    updateStatus(`Registering for ${TARGET_FACILITY}!`, "#00ff00");
                    registerBtn.click();
                    return true;
                } else {
                    updateStatus(`Found ${TARGET_FACILITY}, waiting for Register button to enable...`, "#ffaa00");
                }
            }
            return false;
        }

        // Periodic check loop
        const navInterval = setInterval(() => {
            triggerFacilityRegistration();
            if (scanAndRegister()) {
                clearInterval(navInterval);
            }
        }, 1500);

        const observer = new MutationObserver(() => {
            if (scanAndRegister()) {
                clearInterval(navInterval);
                observer.disconnect();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // ==========================================
        // 3. KEYBOARD SHORTCUT (Alt + R)
        // ==========================================
        window.addEventListener("keydown", (e) => {
            if (e.altKey && (e.key === "r" || e.key === "R" || e.code === "KeyR")) {
                e.preventDefault();
                updateStatus("Manual trigger (Alt+R): Reloading Facility Registration...", "#ffcc00");
                triggerFacilityRegistration();
                setTimeout(scanAndRegister, 600);
            }
        });
    }

})();
