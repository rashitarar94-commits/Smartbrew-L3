# Task B: Selected functionalities

**LLM:** Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code. The code was **fully generated** by the LLM; the conversation is documented in
[`../taskA/05_prompt_log.md` §5.5](../taskA/05_prompt_log.md#55-task-b-code-generation-conversation).

## Selection criteria

1. Each feature covers a **System Description bullet** (no invented scope).
2. Each one is **non-trivial**: it has domain rules, state changes, or cross-cutting concerns, not just CRUD screens.
3. Together they form a **complete loop**: customer → payment → machine state → technician/admin. Each feature can then be demonstrated through the others (e.g. bins fill up because of real orders).
4. Hardware and external services (NFC reader, camera model, payment processor, weather API) are **simulated behind interfaces** so the prototype runs on any PC.

## The 10 functionalities

| # | Functionality | Backlog | Requirements | Why it is non-trivial | Code | Tests |
|---|---|---|---|---|---|---|
| F1 | Accounts: registration, credential login with lockout, NFC card link & tap login, preference profile, auto-logout | PB-01, PB-02, PB-14, PB-15 | FR-01–FR-06, NFR-02 | Hashing, validation, lockout state machine, session timeout, card uniqueness | `smartbrew/auth.py` | `test_f01_auth.py` |
| F2 | Browse categories + real-time customisation (size, milk type, strength, temperature, syrup, extra shot) with live price and nutrition/allergens | PB-03 | FR-08–FR-11 | Ingredient-level recipe model; price and nutrition derived from usage; server-side option validation | `catalog.py`, `shop.py` (`/api/quote`) | `test_f02_f03_menu.py` |
| F3 | Prevent selection of depleted / below-threshold drinks (incl. cups and faults), with reason, enforced on the server | PB-04 | FR-12 | Per-configuration check against stock, thresholds, open faults and bin halt; fallback to another milk type | `machine.check_availability` | `test_f02_f03_menu.py` |
| F4 | Custom recipes: save, name, modify, delete, one-touch ordering | PB-05 | FR-13–FR-16 | Per-user uniqueness, ownership checks, reuse of the customiser in edit mode | `shop.py` (recipes) | `test_f04_recipes.py` |
| F5 | Checkout: card (EMV/contactless), Apple/Google Pay, prepaid employee card; atomic dispense + transaction recording; **offline fallback** | PB-06, PB-12 | FR-22–FR-26, FR-30, NFR-04, NFR-05, NFR-08 | Three payment rules, offline store-and-forward, balance checks, single DB transaction for payment + stock + record | `orders.py` | `test_f05_f06_orders.py` |
| F6 | Receipts via QR code or email (+ order history) | PB-07 | FR-27–FR-29 | QR contains the full receipt (works offline); SMTP or outbox delivery; address not stored | `orders.py` | `test_f05_f06_orders.py` |
| F7 | Personalised recommendations from time of day, weather and history; menu reordering and top-3 highlight with reasons | PB-08 | FR-17, FR-18, NFR-12 | Multi-signal scoring, explainable reasons, offline weather fallback, unavailable items never promoted | `recommend.py` | `test_f07_recommend.py` |
| F8 | Camera mood detection **in memory only**, with consent and a manual fallback; tailored recipe; menu re-ranked by mood | PB-09 | FR-19, FR-20, NFR-01 | Webcam capture in the browser, in-memory decoding and analysis, privacy guarantees tested | `mood.py`, `shop.py` (`/api/mood`) | `test_f08_mood.py` |
| F9 | Secure admin mode (PIN / NFC master card / physical key); refills and counter reset to max; low-stock warnings; waste and grounds bins with warning and **halt on overflow** | PB-10, PB-16 | FR-31–FR-35, NFR-03, NFR-11 | Role gate with timeout; bins filled by real brewing; automatic fault open/close | `admin.py`, `machine.py` | `test_f09_f10_admin.py` |
| F10 | Real-time error messages on the admin dashboard (3 s polling), fault resolution, critical faults block affected drinks, filterable event log with JSON export | PB-11 | FR-36, FR-37 | Live updates, fault scopes (coffee/hot/milk/all), audit trail with actors | `admin.py`, `machine.py`, `templates/admin/` | `test_f09_f10_admin.py` |
| ➕ | *Bonus (optional module):* natural-language drink requests → explicit machine parameters, confirmed by the user | PB-13 | FR-21 | Rule-based interpreter behind an LLM-replaceable interface | `nl_agent.py` | `test_f08_mood.py` |

## Simulated components (prototype boundary)

| Real hardware / service | Prototype stand-in | How to swap in the real one |
|---|---|---|
| NFC reader | Text field "Tap card" (card UID) | Feed the reader's UID into the same `/login/nfc` / prepaid endpoints |
| Camera + facial-expression model | Browser webcam or photo upload → in-memory heuristic in `mood.py` | Replace `estimate_mood()` with an on-device ONNX model |
| Payment processor (EMV, wallets) | `orders.process_payment()` approves with simulated tokens | Call the provider SDK inside `process_payment()` |
| Weather API | Values from the simulation panel; optional live Open-Meteo (`SMARTBREW_WEATHER_LIVE=1`) | Already implemented in `recommend.fetch_live_weather()` |
| Sensors (bins, grinder, heater) | Admin "Simulate" buttons; bins also fill from real orders | Sensors call `machine.raise_fault()` / update `bins` |
| Mail server | `.eml` files in `instance/outbox/` | Set `SMARTBREW_SMTP_HOST` |
| Local LLM | Rule-based `nl_agent.interpret()` | Replace with a llama.cpp call returning the same dict |
