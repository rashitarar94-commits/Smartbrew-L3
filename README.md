# SmartBrew AI – Lab Assignment 3 (Software Engineering with LLMs)

**Repository:** https://github.com/rashitarar94-commits/Smartbrew-L3

SmartBrew AI is an interactive, AI-assisted coffee machine for offices and
lounges, as described in the course System Description. This repository
contains:

| Task | Content | Where |
|---|---|---|
| **A** | LLM-elicited requirements (FR + NFR), user stories, product backlog, comparison with Assignment 2, prompt log | [`docs/taskA/`](docs/taskA/) |
| **B** | Working web prototype with 10 functionalities (+1 optional), LLM-generated | [`smartbrew/`](smartbrew/), [`docs/taskB/feature_selection.md`](docs/taskB/feature_selection.md) |
| **C** | Documented code (docstrings on every function), this README, automated tests | whole repo, [`tests/`](tests/) |

**LLM used:** Claude Opus 5.5 (`claude-opus-5-5`, Anthropic) through Claude
Code (desktop app), for all three tasks. Details are in
[`docs/taskA/05_prompt_log.md`](docs/taskA/05_prompt_log.md).

---

## 1. System overview

The prototype is a **touchscreen-style web app** (Flask + SQLite). It plays
the role of the machine's UI and its control software. Hardware (NFC reader,
camera model, payment terminal, sensors) is simulated behind small,
replaceable interfaces (see
[Simulated components](docs/taskB/feature_selection.md#simulated-components-prototype-boundary)).

```
Browser (kiosk UI) ──HTTP──▶ Flask app (smartbrew/)
                               ├─ auth.py        accounts, NFC login, profile
                               ├─ shop.py        menu, customiser, recipes, mood, assistant
                               ├─ orders.py      checkout, payments, receipts, history
                               ├─ admin.py       secure admin mode, dashboard, event log
                               ├─ catalog.py     options → ingredients, price, nutrition
                               ├─ machine.py     inventory, bins, faults, availability, events
                               ├─ recommend.py   time/weather/history/mood scoring
                               ├─ mood.py        in-memory image → mood (no storage)
                               ├─ nl_agent.py    free text → machine parameters
                               └─ db.py          SQLite schema + demo seed data
```

### Repository layout

```
├── README.md               ← you are here
├── requirements.txt        pinned Python dependencies
├── run.py                  start script (python run.py [--reset] [--port N])
├── smartbrew/              application package (Python, Jinja templates, CSS)
├── tests/                  pytest suite: one file per functionality (50 tests)
├── samples/                synthetic face images for the mood demo (no webcam needed)
├── tools/                  helper script that regenerates samples/
└── docs/
    ├── taskA/              00 system description … 05 prompt log
    └── taskB/              feature selection + simulated components
```

## 2. Environment & prerequisites

| Item | Version / note |
|---|---|
| OS | Developed and tested on **Windows 11** (also runs on macOS/Linux; those were not tested) |
| Python | **3.15.1** (tested). Any Python ≥ 3.10 should work but was not tested |
| Python packages | `Flask 3.1.3`, `Werkzeug 3.1.9`, `qrcode 8.2`, `pillow 13.0.0`, `pytest 9.1.1` (pinned in `requirements.txt`) |
| Database | SQLite (built into Python). It is created automatically in `instance/smartbrew.sqlite` |
| Browser | Any modern browser (Chrome, Edge, Firefox). A webcam is optional |
| Network | **Not required.** All external services are simulated; the app runs fully offline |

No compiler, Node.js, or external database is needed.

## 3. Installation (build)

**Windows (PowerShell):**

```powershell
git clone https://github.com/rashitarar94-commits/Smartbrew-L3.git smartbrew
cd smartbrew
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

**macOS / Linux:**

```bash
git clone https://github.com/rashitarar94-commits/Smartbrew-L3.git smartbrew && cd smartbrew
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

(The commands call the virtual environment's Python directly, so you do not
need to "activate" it. This also avoids PowerShell's execution-policy prompt.)

## 4. Running

```powershell
.venv\Scripts\python run.py --reset
```

Open **http://127.0.0.1:5000** in a browser. `--reset` starts from fresh demo
data. Leave it out to keep the data between runs. Stop the server with `Ctrl+C`.

### Demo data (local test values, seeded by `smartbrew/db.py`)

| What | Value |
|---|---|
| User **alice** | password `password123`, NFC/prepaid card `04AA11BB`, €20 prepaid, history of lattes, prefers oat milk |
| User **bob** | password `password123`, no card, €5 prepaid, history of espressos |
| Technician PIN | `4321` |
| NFC master card | `MASTER-0001` |
| Physical key ID | `KEY-SB-01` |

### Running the automated tests

```powershell
.venv\Scripts\python -m pytest -v
```

Expected result: **50 passed**. The tests use a temporary database and never
touch `instance/`. Each test file covers one or two functionalities
(`test_f01_…` to `test_f09_f10_…`).

### Optional configuration (environment variables)

| Variable | Effect | Default |
|---|---|---|
| `SMARTBREW_INACTIVITY` | Auto-logout after N seconds without interaction | `60` |
| `SMARTBREW_WEATHER_LIVE=1` | Use live weather from Open-Meteo (falls back to simulated values on any error) | off |
| `SMARTBREW_LAT` / `SMARTBREW_LON` | Machine location for live weather | Stockholm |
| `SMARTBREW_SMTP_HOST` / `SMARTBREW_SMTP_PORT` | Send receipt emails via SMTP instead of writing them to `instance/outbox/` | off / 25 |
| `SMARTBREW_SECRET` | Flask session secret | dev value |

## 5. Execution guide: demonstrating the 10 functionalities

Start with `python run.py --reset` and follow the steps in order. Each
step names the backlog item (PB-xx) and the test file that checks it
automatically. The **🔧** link in the top-right corner opens the
maintenance area.

### F1 – Accounts, NFC login, preferences, auto-logout (PB-01/02/14/15)
1. Click **Register** and create `carol` / `carol@example.com` / `secret123`. You are logged in and see "👤 carol".
2. Click **Log out**, then **Log in** with a wrong password → *Invalid credentials*. Log in correctly.
3. Open **👤 carol** (profile) → *NFC card* → enter `04A1B2C3` → **Link card**.
4. **Log out** → **Log in** → *Tap NFC card* → enter `04A1B2C3` → **Tap card** → logged in as carol.
5. In the profile, set *Default milk = Oat milk*, *Strength = 5* → **Save preferences**. Open any milk drink: the customiser starts with oat milk and strength 5.
6. Leave the browser idle for 60 s → you are returned to the public menu.
7. *(Lockout)* Enter a wrong password for `bob` 5 times → the 6th attempt says the account is locked.

*Automated:* `tests/test_f01_auth.py`

### F2 – Browse, real-time customisation, nutrition (PB-03)
1. On **Menu**, click the category tabs (*Coffee, Milk coffee, Chocolate, Tea, Cold drinks*).
2. Open **Cappuccino**. Change *Size → L*, *Milk → Oat milk*, *Strength → 5*, *Syrup → 2*, tick *Extra shot*.
3. The price, the summary line and the **Nutrition** table (kcal, sugar, fat, caffeine, allergens such as "oats (gluten)") update immediately, without reloading the page.

*Automated:* `tests/test_f02_f03_menu.py`

### F3 – Block unavailable drinks (PB-04)
1. Open **🔧** → enter PIN `4321`.
2. In *Ingredients*, click **Empty (demo)** for *Whole milk*, *Oat milk* and *Lactose-free milk*.
3. Open **Menu**: all milk drinks are greyed out with "⚠ Out of … milk" and cannot be clicked. Espresso and Americano are still available.
4. Empty only *Whole milk* instead: Latte stays available, but in the customiser the *Whole milk* option is disabled.
5. Click **Reset to max** for the milks to restore them.

*Automated:* `tests/test_f02_f03_menu.py` (also checks that the server rejects a forged order)

### F4 – Custom recipes (PB-05)
1. Log in as `alice` (or tap card `04AA11BB`).
2. Open **Flat White**, customise it, type the name *Monday fuel* → **⭐ Save as recipe**.
3. **My recipes** shows the recipe. Click **Edit** → change strength and name → **Update recipe**.
4. On the **Menu**, the "⚡ One-touch" bar shows the recipe. One click opens checkout pre-configured.
5. **Delete** removes it. Saving the same name twice is refused.

*Automated:* `tests/test_f04_recipes.py`

### F5 – Payment, dispensing, transaction recording, offline fallback (PB-06/12)
1. As `alice`, order any drink → checkout → *Prepaid employee card* (card `04AA11BB` is pre-filled) → **Pay & brew**.
2. The receipt appears. The profile shows the reduced prepaid balance. **History** lists the order with every parameter (milk, strength, temperature, syrup, size).
3. Order again with *Credit/Debit card*, *Apple Pay* or *Google Pay* → approved (simulated; no card number is ever requested).
4. Log in as `bob` (€5 prepaid). In the profile, link card `0B0B0B0B`. Order a *Mocha*, size L, with 3 syrup shots and an extra shot (€5.50), and pay with *Prepaid employee card* → *Insufficient prepaid balance*. Nothing is dispensed.
5. **Offline:** 🔧 → *Simulation panel* → untick **Network online** → **Apply**. A yellow *Offline mode* banner appears. Wallets are disabled, the weather chip says "unavailable", and a card payment is accepted with the badge "offline – pending sync".
6. Tick **Network online** again.

*Automated:* `tests/test_f05_f06_orders.py`

### F6 – Receipts by QR code or email (PB-07)
1. After any order, the receipt page shows a **QR code**. Scan it with a phone: it contains the full receipt text and URL.
2. Enter an email address → **Send**. Without SMTP configured, the message is saved as `instance/outbox/receipt-<no>.eml`, which opens in any mail client.
3. You can also choose *Email* directly at checkout.

*Automated:* `tests/test_f05_f06_orders.py`

### F7 – Personalised recommendations & menu reordering (PB-08)
1. Log in as `alice`. *Recommended for you* shows **Latte** first with the reason "You often order Latte". The whole menu is sorted by score.
2. 🔧 → *Simulation panel*: set *Temperature 3*, *Weather rainy*, *Hour 15* → **Apply**. As a guest (log out), Hot Chocolate and tea rise, and iced drinks drop to the bottom.
3. Set *Temperature 30*, *Weather sunny* → iced drinks are highlighted at the top.
4. Set *Hour 20* → caffeine drinks drop and tea/chocolate rise ("Evening → less caffeine").
5. Clear the hour field to use the real clock again.

*Automated:* `tests/test_f07_recommend.py`

### F8 – Mood detection (in memory) & tailored drink (PB-09)
1. Click **Mood** → tick the **consent** box.
2. Either **Start camera** → **Analyse my mood**, or upload one of the sample images in `samples/` (`tired.png`, `happy.png`, `stressed.png`).
3. The estimated mood and a tailored recipe appear. For example, *tired* → Double Espresso, strength 5, with an extra shot. **Customise & order** opens it.
4. Back on the **Menu**, a "Mood: tired" chip is shown and the ranking reflects it (✕ forgets the mood).
5. Without consent, the camera and upload stay disabled. The manual mood buttons always work.
6. Privacy check: no image is written anywhere. Look in `instance/`: only the database and the outbox exist. The event log records only the mood label.

*Automated:* `tests/test_f08_mood.py`, including a test that no file or log entry contains the image.

> The prototype's classifier is a simple, explainable image heuristic
> (brightness, contrast, saturation). A webcam photo of a real face will
> usually be classified as *neutral* or *happy*. Use the sample images or the
> manual buttons to demonstrate every mood. See
> [`smartbrew/mood.py`](smartbrew/mood.py) for how to plug in a real model.

### F9 – Secure admin mode, refills, bins (PB-10/16)
1. Click **🔧**. Try PIN `0000` → *Access denied* (logged). Then use PIN `4321`, master card `MASTER-0001`, or key `KEY-SB-01`.
2. *Ingredients*: **Add** a quantity (capped at capacity) or **Reset to max**. Ingredients below 20 % show **LOW**, and a "Low Ingredient Threshold" warning appears under *Live errors*.
3. *Waste bins*: enter 85 → **Simulate fill %** → *Warning*. Enter 100 → *Full*: a red "Operations halted" banner appears and no drink can be ordered.
4. **Mark emptied** → the bin returns to 0 % and ordering resumes.
5. Bins also fill from real orders: every coffee adds grounds, and every drink adds rinse water.

*Automated:* `tests/test_f09_f10_admin.py`

### F10 – Real-time errors & event log (PB-11)
1. On the dashboard, choose *Grinder Jammed* → **Simulate sensor fault**. The error appears under *Live errors*, and the panel refreshes every 3 s without reloading.
2. Open the **Menu** in a second tab: all coffee drinks are unavailable ("Grinder Jammed"), while tea and hot chocolate still work. *Water Heater Fault* blocks all hot drinks.
3. Click **Resolve** → the error disappears and "Resolved: Grinder Jammed" is logged with the technician's name.
4. **📜 Event log** → filter by type/severity → **⬇ Export JSON** for remote diagnostics (`/admin/api/events`).

*Automated:* `tests/test_f09_f10_admin.py`

### ➕ Optional: natural-language drink request (PB-13)
1. Click **Ask** → type *"Give me something sweet with a kick, but low on dairy"* (or click an example).
2. The proposal shows the drink and the explicit parameters (Americano, oat milk, 2 syrup, strength 5, extra shot), with one line per interpretation step. **Review & order** opens the customiser for confirmation.

## 6. Code documentation

Every function and method in `smartbrew/`, `tests/`, `run.py` and `tools/`
has a docstring that gives its **purpose**, **Inputs** and **Returns**
(and **Raises** where relevant). Requirement IDs (FR-xx / NFR-xx) are
referenced in the docstrings to give traceability back to Task A.

## 7. Known limitations

* Hardware and payment providers are simulated (see the table in [`docs/taskB/feature_selection.md`](docs/taskB/feature_selection.md#simulated-components-prototype-boundary)).
* The development server (`run.py`) is not meant for production. There is no CSRF protection or HTTPS in this prototype.
* Offline card transactions are flagged but not synced to a real processor (PB-17 is not implemented).
