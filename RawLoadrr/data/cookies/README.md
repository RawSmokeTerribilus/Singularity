This directory is for saving your cookies automatically generated during RawLoadrr setup.

## Cookie Management (v1.6)

### Automatic Generation (Recommended)
The script will generate cookie files automatically when you:
1. Configure tracker URLs and API keys in `config/.env`
2. Run RawLoadrr through the TUI (Singularity menu → RawLoadrr)
3. Authenticate with your tracker account

Cookie file will be saved here as: `<tracker_name>_cookies.txt`

### Manual Setup
If you need to manually add cookies:
1. Log in to your tracker in a browser
2. Use browser DevTools (F12) → Application → Cookies
3. Copy the essential cookies (typically `session`, `PHPSESSID`, or tracker-specific)
4. Place in a `.txt` file in this directory: `/app/RawLoadrr/data/cookies/tracker_name.txt`

### Private Tracker Notes (PTP, BTN, etc.)
For trackers like PTP (PassThePopcorn):
- Cookie auto-generation is disabled for security reasons
- You MUST manually provide cookie via browser extraction
- Rename to: `ptp_cookies.txt`
- Keep this file **outside git** (added to `.gitignore`)

### Security & Privacy (v1.6)
- Cookies are stored locally in your workspace (never uploaded)
- If running in Docker, cookies persist in the volume `./work_data/cookies/` (synced to host)
- Use a `.env` file for API keys (not cookies)
- All cookie files are tracked as ignored in git

---

*Updated for Singularity Core v1.6 — Cookie handling integrated with HardwareAgent + FAST_WORK_DIR pipeline*
