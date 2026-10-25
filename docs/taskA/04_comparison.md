# 4. Comparison: LLM-generated vs. human-elicited (Assignment 2) artifacts

* **Human baseline:** *Task2b Lab2 (G33)*: 10 user stories (IDs 1–7, 9–11), 14 requirements, 10 backlog items. No non-functional requirements.
* **LLM output:** Claude Opus 5.5: 37 functional + 14 non-functional requirements, 22 user stories, 17 backlog items, and 7 suggestions that the team rejected.
* **Prompt used for the comparison:** P5 in [`05_prompt_log.md`](05_prompt_log.md). Every finding below was checked manually against both documents by the team.

## 1. Method and threats to validity

1. The LLM was told to elicit from the **System Description** (P1–P4). However, the Lab 2 document had already been shared earlier in the **same session**: at first it was the only material available, before the System Description was supplied. The elicitation is therefore **not blind** to the human artifacts. The LLM may have been anchored on Lab 2 wording, and the overlap counts in §2 may be slightly inflated. A blind replication would use a fresh session containing only P1–P4.
2. The comparison was then produced by the same LLM (P5) and reviewed by the team, who checked every claim against the original `.docx`. The team rewrote or removed findings that were wrong.
3. **Threat:** the LLM was told the target format (taken from Assignment 2), so similarity in *structure* is by design and not a finding.
4. **Threat:** the LLM's numeric values (thresholds, time-outs, estimates) are invented defaults. They have **not** been validated with stakeholders (see §3, point M1).

## 2. Quantitative overview

| Artifact | Assignment 2 (human) | LLM | Covered by both | Only LLM (new) | Only human |
|---|---|---|---|---|---|
| Functional requirements | 14 | 37 (+7 rejected) | 14 | 23 | 0 |
| Non-functional requirements | 0 | 14 | 0 | 14 | 0 |
| User stories | 10 | 22 | 10 | 12 | 0 |
| Backlog items | 10 | 17 | 9 | 8 | 1 (merged, see §2.3) |

How the System Description bullets are covered (18 bullets, counting the
two LLM-agent sub-bullets as one):

| System Description bullet | Lab 2 | LLM |
|---|---|---|
| Account, credentials/NFC login, **preference profile** | ✔ (profile only in story 1) | ✔ FR-01–FR-06 |
| **Record every transaction with customisation parameters** | ✘ | ✔ FR-26 |
| Save / modify / name recipes, **one-touch ordering** | ✔ (no one-touch) | ✔ FR-13–FR-16 |
| **Recommendations from time of day, weather, history** | ✘ | ✔ FR-17 |
| Camera mood → tailored recipe | ✔ | ✔ FR-19, FR-20 |
| **Reorder/highlight menu by score** | ✘ | ✔ FR-18 |
| Browse categories, nutrition, **real-time customisation** | ◐ (no customisation) | ✔ FR-08–FR-11 |
| Block depleted ingredients | ✔ | ✔ FR-12 |
| **Cards / wallets / prepaid employee cards** | ✘ | ✔ FR-22–FR-24 |
| Receipt QR / email | ✔ | ✔ FR-27, FR-28 |
| **Local LLM agent (optional)** | ✘ | ✔ FR-21 |
| **Secure admin mode (key / NFC master / PIN)** | ✘ (only "technician authorized") | ✔ FR-31 |
| Refills + reset counters (incl. **cups**) | ✔ (cups not mentioned) | ✔ FR-32 |
| Waste/grounds bins, **halt on overflow** | ◐ (no halting) | ✔ FR-34, FR-35 |
| Real-time errors on dashboard **and event logs for remote diagnostics** | ◐ (no event log) | ✔ FR-36, FR-37 |
| **In-memory facial image processing** | ✘ | ✔ NFR-01 |
| **Offline fallback** | ✘ | ✔ FR-30, NFR-05 |
| **Coverage** | **7 ✔ · 3 ◐ · 8 ✘** | **18 ✔** |

## 3. Side-by-side differences (diff notation)

`-` red = Assignment 2 text that was changed or that the LLM considers wrong or
incomplete · `+` green = LLM text · lines without a sign are unchanged in
meaning.

### 3.1 Requirements

```diff
  1  Registering a new user account | Username, email, password
+ FR-01 ... + password confirmation; unique email; min. 8 chars incl. letter & digit; salted hash
  2  Log in users using credentials
+ FR-02 ... + lockout after 5 failed attempts (5 min); generic error message
  3  Login user using NFC/card tap
+ FR-03 Link an NFC card to the account          (Lab 2 never says how a card gets "registered")
+ FR-05 Logout + 60 s inactivity auto-logout     (shared office kiosk)
+ FR-06 Preference profile (milk, strength, temperature, dietary flags)
+ FR-07 Basic manual ordering for guests
  4  Save and name a custom beverage recipe
  5  Modify a saved beverage recipe
+ FR-15 Delete a saved recipe
+ FR-16 One-touch ordering of a saved recipe
- 6  Display available beverage categories | Inputs: Category selection | Outputs: Available beverage categories
+ FR-08 Display beverage categories | Inputs: Home screen   (input ≠ output in Lab 2)
  7  Display drinks in a selected category
+ FR-10 Real-time customisation: size, milk type, strength, temperature, syrup shots, extra shot; live price
- 8  Disable unavailable drinks | Inputs: Ingredient availability status | Outputs: Disabled drink option
+ FR-12 ... + includes cups; shows the reason ("Out of milk"); enforced by the server too; re-checked after each dispense/refill
- 9  Deliver receipt through QR code or email   (one requirement, two mechanisms)
+ FR-27 Receipt via QR code
+ FR-28 Receipt via email
- 10 Analyze facial expressions to estimate mood and suggest drinks
+ FR-19 ... moods: tired / happy / stressed / neutral; tailored recipe (e.g. extra shot)
+ FR-20 Explicit consent + manual mood picker fallback
+ NFR-01 Images processed in memory only, never stored or transmitted
  11 Display nutritional information for a selected beverage
+ FR-11 ... for the *customised* configuration + allergens
+ FR-17 Recommendation score from time of day, weather, history, profile
+ FR-18 Reorder menu by score, highlight top-3 with a reason
+ FR-21 Local LLM agent: natural language → explicit machine parameters (optional)
+ FR-22 Credit/debit card (EMV / contactless)
+ FR-23 Apple Pay / Google Pay
+ FR-24 Prepaid employee card with balance
+ FR-25 Dispense: deduct ingredients incl. cups; increase waste/grounds levels
+ FR-26 Record every transaction with all customisation parameters
+ FR-29 Order history
+ FR-30 Offline fallback (manual ordering, offline card processing, wallets disabled)
+ FR-31 Secure admin mode: physical key / NFC master card / technician PIN
- 12 Register ingredient refills and reset counters | Precondition: Technician authorized
+ FR-32 ... ingredients incl. cups; "add quantity" OR "reset to max"; availability re-evaluated; event logged
+ FR-33 Low Ingredient Threshold warning
- 13 Monitor liquid waste and coffee grounds bin capacities | Postcondition: Technician alerted
+ FR-34 ... warn at ≥ 80 %; HALT operations at 100 %
+ FR-35 Register bin emptied → reset + resume
- 14 Display real-time machine errors on the admin dashboard
+ FR-36 ... with severity; acknowledge/resolve; critical faults block ordering
+ FR-37 Persistent, filterable, exportable event log for remote diagnostics
+ NFR-01 … NFR-14 (14 non-functional requirements; Lab 2 had none)
```

### 3.2 User stories

```diff
- 1  As a user, I want to create an account and log in using my credentials or an NFC card,
-    so that I can keep my profile of personal preferences.
+ US-01 ... log in with my credentials ...                         (split: one story per login mechanism)
+ US-02 ... link my NFC badge and log in by tapping it ...
+ US-03 ... store default milk, strength, temperature, dietary flags ...   (the "profile" Lab 2 mentions but never specifies)
+ US-04 ... be logged out automatically when I walk away ...
  2  save, name, and modify custom beverage recipes          → US-09 (+ delete)
+ US-10 order a saved recipe with one touch
  3  browse beverage categories                              → US-05
+ US-06 customise milk / strength / temperature / syrup with instant price
  4  disable drinks whose ingredients are not available      → US-08 (+ reason shown)
  5  receive my receipt through a QR code or email           → US-15
- 6  As a user I want the machine to use my facial expression to suggest a suitable drink.
+ US-12 ... consent asked first; image never stored                 (privacy constraint added)
  7  view nutritional information                            → US-07 (+ allergens, per configuration)
- 8  (missing: numbering jumps from 7 to 9)
+ US-11 recommendations by time of day / weather / history; menu reordered
+ US-13 describe my drink in my own words (local LLM)
+ US-14 pay with bank card, phone wallet or employee prepaid card
+ US-16 see past orders
+ US-17 keep working when the network is down
+ US-18 (technician) enter admin mode with key / master card / PIN
  9  (technician) register refills and reset counters        → US-19
- 10 (technician) alerts when liquid waste or grounds bins need emptying or refill.
+ US-20 ... AND halt the machine when full; "emptied" resets      ("or refill" in Lab 2 mixes bins with ingredients)
+ US-21 (technician) low-ingredient warnings
- 11 (admin) real-time error messages and event logs on the admin panel.  → no "how to verify"
+ US-22 ... "Grinder Jammed" visible in ≤ 5 s; resolution logged; export JSON for remote diagnostics
+ Every LLM story has acceptance criteria and traces to FR IDs (Lab 2 had neither)
```

### 3.3 Product backlog

```diff
  1  Register into the system (20/2)                      ┐
  2  Login into the system (30/2)                         ┘→ PB-01 Register & log in (30/2)   (merged)
+ PB-02 NFC card link & tap login (25/2)                  (Lab 2 req 3 had NO backlog item)
  3  Save and name custom beverage recipe (15/4)          ┐
  4  Modify custom beverage recipe (15/3)                 ┘→ PB-05 Custom recipes incl. one-touch (25/3)
- 5  Display Adavale drinks (30/3)                        (typo "Adavale" = Available)
+ PB-03 Browse + real-time customisation + nutrition (30/4)
+ PB-04 Block unavailable drinks (30/3)                   (separated so it can be demonstrated on its own)
- 6  Analyze facial expressions ... "When I detect your mood, I'll be sure to recommend a drink.
-    Use different phrases and search suggestions."       (first-person LLM-style text; not a test step)
+ PB-09 Mood detection (in-memory) + tailored suggestion (20/4): consent → capture → mood → suggestion; verify no file stored
  7  Display nutritional information (10/3)               → part of PB-03
  8  Delivery receipt through QR code or mail (20/3)      → PB-07 (20/2)
- 8  "...order it and pay for it."                        (payment demonstrated but never specified)
+ PB-06 Checkout: card / wallet / prepaid + transaction recording (30/4)
  9  Register ingredient refills and reset counters (30/"5.")  → PB-10 (30/4) + secure admin mode
- 10 Monitor liquid waste level (30/4)                    (grounds bin dropped although req 13 has it)
+ PB-10 ... both bins, warning ≥ 80 %, halt at 100 %
+ PB-08 Personalised recommendations + menu reordering (25/4)
+ PB-11 Real-time error dashboard + event log (25/3)      (Lab 2 story 11 / req 14 had NO backlog item)
+ PB-12 Offline fallback · PB-13 Local LLM · PB-14 Profile · PB-15 Auto-logout · PB-16 Low-stock · PB-17 Offline sync
```

## 4. Analysis

### 4.1 What the LLM improved

| # | Improvement | Evidence |
|---|---|---|
| I1 | **Coverage of the System Description**: 18/18 bullets vs 7 full + 3 partial in Lab 2. Payments, transaction recording, recommendations, menu reordering, admin mode, privacy, offline fallback and the LLM agent were all missing in Lab 2. | §2 table |
| I2 | **Non-functional requirements** (14), each with a measurable criterion. Lab 2 had none, although the System Description itself states two NFRs: in-memory image processing and offline resilience. | NFR-01…14 |
| I3 | **Acceptance criteria and traceability** (story → FR → backlog). Lab 2 had no explicit links. | US table, PB "Story" column |
| I4 | **Atomic requirements**: Lab 2 req 9 (QR *or* email) and story 1 (credentials *or* NFC) were split into one requirement per mechanism, so each can be tested on its own. | FR-27/28, US-01/02 |
| I5 | **Missing supporting functions**: linking an NFC card (otherwise req 3 cannot work), deleting recipes, emptying bins, logout. | FR-03, FR-15, FR-35, FR-05 |
| I6 | **Defect detection in Lab 2**: missing story 8; typos ("Adavale", "exit" → exist, estimate "5."); req 6 lists the output as its own input; NFC (req 3) and admin errors (story 11 / req 14) have no backlog item; backlog 10 drops the grounds bin; backlog 6 contains first-person, non-testable text; story 10 says "emptying **or refill**" for bins. | §3 diffs |
| I7 | **Safety and privacy thinking**: consent before camera use, generic login error messages, account lockout, no card data stored, halting on bin overflow. | FR-02, FR-20, NFR-01, NFR-04, FR-34 |

### 4.2 What the LLM missed or did poorly

| # | Weakness | Comment |
|---|---|---|
| M1 | **Invented numbers ("hallucinated precision").** It produced 5 login attempts, a 60 s timeout, warn at 80 %, 20 % low-stock, ≤ 5 s refresh, < 2 s inference. None of these come from the System Description. | Accepted as *defaults to be validated with the customer*, not as facts. |
| M2 | **Ambiguity left unresolved:** it treated the NFC login card and the *prepaid employee card* as two separate cards. In an office they are very likely the **same badge**. The human team (Lab 2) also never asked this question. | Added as an open question; the prototype lets one card UID be used for both. |
| M3 | **Location for weather data was never addressed.** Weather-based recommendations need the machine's location (configuration or IP lookup), which is a privacy and configuration concern. | Added note: location is a configured setting, not user data. |
| M4 | **Guest e-mail receipts collect personal data** (an email address) without any retention rule. The LLM wrote NFR-06-style privacy rules for accounts only. | Noted; guest emails are not stored in the prototype. |
| M5 | **Generic estimates.** Effort values are not based on the team's real velocity. E.g. *mood detection = 4 days* is optimistic for a real CV model and pessimistic for a stub. | Team kept the scale but treats the numbers as relative only. |
| M6 | **Scope inflation**: 37 FRs versus 14, plus 7 "nice-to-have" ideas (§5). Without human filtering the backlog would not fit the time available. | 7 suggestions rejected; PB-12…PB-17 left out of the Task B prototype. |
| M7 | **Some overlap in its own output**: PB-16 (low-stock warnings) duplicates part of PB-10/PB-11, and US-21 overlaps FR-33/FR-36. It was found only in the self-review prompt (P4). | Kept as one item in the prototype. |
| M8 | **Lab 2 had concrete "how to demonstrate" steps tied to the group's own UI screens** (e.g. "go to profile page, choose Custom Recipe"). The LLM steps are similar, but initially referred to generic screens. They were rewritten after the prototype existed. | Human knowledge of the actual UI is better. |

## 5. Rejected LLM suggestions (with justification)

| ID | LLM suggestion | Justification for rejection |
|---|---|---|
| X-01 | Loyalty programme (points → free drinks) | Not in the System Description. In a corporate office with prepaid employee cards, drinks are typically subsidised by the employer, so a loyalty programme adds no value and conflicts with the employer's billing. |
| X-02 | Automatic ingredient re-ordering from suppliers | Needs integration with procurement/ERP systems that are outside the machine's boundary. The description only requires *technician* refills and alerts. |
| X-03 | Voice ordering | Not requested. A microphone adds new privacy risks (always-listening device in an office) on top of the camera. Natural-language input is already covered by the optional local LLM with typed text (FR-21). |
| X-04 | Multi-language UI | Useful but not a requirement. It does not change the architecture, so it is **deferred** to a later release. |
| X-05 | Sales / revenue analytics | Business reporting is outside the described scope (personalisation, payment, maintenance). The event log (FR-37) already supports remote diagnostics. Deferred. |
| X-06 | Software-controlled descaling / cleaning cycles | This is machine firmware / hardware behaviour, not part of the interactive system described. It cannot be specified meaningfully without hardware documentation. |
| X-07 | Sharing recipes with colleagues / social feed | Not in scope. It brings moderation and privacy issues (it exposes colleagues' dietary habits) without supporting any stated goal. |

### Accepted with modification

| LLM proposal | Modification by the team |
|---|---|
| FR-05 auto-logout after 60 s | Kept, but the value is configurable (M1). |
| FR-19 mood detection with a CV model | Kept. The **prototype** uses a lightweight in-memory image heuristic instead of a trained model, documented as a replaceable component. |
| FR-21 local LLM agent | Kept as **optional** (matches the description). The prototype has a rule-based parser behind the same interface. |
| FR-22/23 real card & wallet processing | Simulated in the prototype; no real payment provider. |
