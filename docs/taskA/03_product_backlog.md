# 3. Product Backlog (LLM-generated)

Model: Claude Opus 5.5 · Prompt: P3 in [`05_prompt_log.md`](05_prompt_log.md)

Same columns as Assignment 2: **Imp** (importance, higher = more important,
same 10–30 scale) and **Est** (estimate in ideal days). Items are sorted by
importance. **★** marks the items implemented in the Task B prototype (see
[`../taskB/feature_selection.md`](../taskB/feature_selection.md)).

| ID | Name | Imp | Est | How to demonstrate | Notes | Story | Lab2 |
|---|---|---|---|---|---|---|---|
| PB-01 ★ | Register & log in (credentials) | 30 | 2 | Open *Register*, enter username, email and password, and submit → logged in. Log out, then log in again. Enter a wrong password → error. | Hash passwords; lockout after 5 failures | US-01 | 1, 2 |
| PB-02 ★ | NFC card link & tap login | 25 | 2 | In *Profile*, link card UID `04A1B2C3`. Log out, choose *Tap card*, enter/scan the UID → logged in. | Simulated reader in the prototype | US-02 | — |
| PB-03 ★ | Browse menu + real-time customisation + nutrition | 30 | 4 | Open the menu, pick *Cappuccino*, change milk to oat, strength 4, 2 syrup shots → price and nutrition panel update live. | Nutrition computed from per-ingredient data | US-05, US-06, US-07 | 5, 7 |
| PB-04 ★ | Block unavailable drinks | 30 | 3 | In admin mode, set milk to 0. Back on the menu, all milk drinks are greyed out with "Out of milk", and a direct order request is rejected. | Per-ingredient minimum threshold; cups included | US-08 | 5 |
| PB-05 ★ | Custom recipes (save / name / edit / delete / one-touch) | 25 | 3 | Customise a drink → *Save as recipe* "Monday fuel". In *My recipes*, edit it, order it with one touch, and delete it. | Unique name per user | US-09, US-10 | 3, 4 |
| PB-06 ★ | Checkout: card / wallet / prepaid + transaction recording | 30 | 4 | Order a drink and pay with *Prepaid employee card* → balance decreases. Pay with a card → approved. History shows the order with all parameters. | Payment gateway simulated; no PAN stored | US-14, US-16 | — |
| PB-07 ★ | Receipts via QR code or email | 20 | 2 | After paying, a QR code is shown; scanning or opening it shows the receipt. Choose *Email* → a message appears in the `outbox/` folder (or is sent via SMTP if configured). | Email delivery stubbed for offline grading | US-15 | 8 |
| PB-08 ★ | Personalised recommendations + menu reordering | 25 | 4 | Log in as `alice` (seeded history of lattes). On the menu, latte is first with a "Recommended" badge and a reason. Change the simulated weather to *cold & rainy* → hot chocolate rises. | Score = time + weather + history + profile | US-11 | — |
| PB-09 ★ | Mood detection (in-memory) + tailored suggestion | 20 | 4 | Click *Mood suggestion*, accept consent, capture a webcam frame (or upload a photo) → mood + tailored recipe (e.g. *tired* → extra shot). Check that no image file was created. | Prototype uses a lightweight image heuristic; a real model can be swapped in | US-12 | 6 |
| PB-10 ★ | Secure admin mode + refills + bins | 30 | 4 | Enter technician PIN → admin panel. Reset milk to max → milk drinks re-enabled. Dispense until the grounds bin is ≥ 80 % → warning; at 100 % → ordering halted; press *Emptied* → resumed. | PIN hashed; NFC master card also accepted | US-18, US-19, US-20, US-21 | 9, 10 |
| PB-11 ★ | Real-time error dashboard + event log | 25 | 3 | In admin mode, inject "Grinder Jammed" → it appears on the dashboard within 3 s and coffee ordering is blocked. Resolve it → logged. Filter the log and export JSON. | Polling every 3 s | US-22 | — |
| PB-12 | Offline fallback | 20 | 3 | Toggle *Network offline* in the simulation panel → banner shown; wallets disabled; weather ignored; card payment queued offline. | Partially in the prototype (simulation toggle) | US-17 | — |
| PB-13 | Local LLM natural-language ordering | 10 | 5 | Type "something sweet with a kick, low on dairy" → proposed configuration to confirm. | Optional module; prototype ships a rule-based stand-in | US-13 | — |
| PB-14 | Preference profile | 15 | 2 | Set default oat milk + lactose-free → the customiser pre-fills oat milk. | | US-03 | — |
| PB-15 | Auto logout after inactivity | 15 | 1 | Wait 60 s → returned to the public home screen. | | US-04 | — |
| PB-16 | Low-ingredient warnings | 15 | 1 | Drop beans below 20 % → "Low Ingredient Threshold" event on the dashboard. | Covered inside PB-10/PB-11 in the prototype | US-21 | — |
| PB-17 | Offline transaction sync | 10 | 3 | Bring the network back → queued offline card transactions are synced. | Requires a real payment processor | US-17 | — |
