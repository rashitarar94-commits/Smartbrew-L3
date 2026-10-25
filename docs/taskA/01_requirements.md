# 1. Functional and Non-Functional Requirements (LLM-generated)

| | |
|---|---|
| **Model** | Claude Opus 5.5 (`claude-opus-5-5`, Anthropic), used through the Claude Code desktop app |
| **Date** | 25-Oct-2026 |
| **Input** | [`00_system_description.md`](00_system_description.md) + the table format of Assignment 2 |
| **Prompts** | P1–P3 in [`05_prompt_log.md`](05_prompt_log.md) |

The format follows Assignment 2 (ID, Description, Inputs, Outputs,
Precondition, Postcondition). The **Lab2** column gives the matching
Assignment 2 requirement number. **NEW** means the requirement has no
equivalent in Assignment 2. Requirements the LLM suggested but the team
rejected are listed in §1.3. Their justifications are in
[`04_comparison.md` §4](04_comparison.md#4-rejected-llm-suggestions-with-justification).

## 1.1 Functional Requirements

### A. Accounts, authentication and profile

| ID | Lab2 | Description | Inputs | Outputs | Precondition | Postcondition |
|---|---|---|---|---|---|---|
| FR-01 | 1 | Register a new user account. The email must be unique and well-formed, and the password must have at least 8 characters including a letter and a digit. | Username, email, password, confirmation | Confirmation, or a validation error naming the field | No account with the same username/email | Account stored with a salted password hash |
| FR-02 | 2 | Log in with credentials. After 5 consecutive failures the account is locked for 5 minutes. | Username/email, password | Personalised home screen, or a generic "invalid credentials" error | Account exists and is not locked | Session created; failure counter reset |
| FR-03 | NEW | Link an NFC/contactless card to the logged-in account. | Card UID from the NFC reader | "Card linked", or "card already in use" | User logged in; card not linked elsewhere | Card UID stored for the account |
| FR-04 | 3 | Log in by tapping a linked NFC card. | Card UID | Personalised home screen, or "unknown card" | Card linked to an active account | Session created |
| FR-05 | NEW | Log out manually, and log out automatically after 60 s of inactivity (shared office kiosk). | Logout button / inactivity timer | Public home screen | User logged in | Session destroyed |
| FR-06 | NEW (story 1 only) | Maintain a personal preference profile: default milk type, strength, temperature, and dietary flags (lactose-free, low-sugar, decaf). | Preference values | Saved profile; defaults pre-filled in customisation | User logged in | Profile stored and used by recommendations |
| FR-07 | NEW | Basic manual ordering for guests (no account). | Drink selection | Standard order flow, without recipes or history | — | Order processed as guest |

### B. Menu, customisation, nutrition and availability

| ID | Lab2 | Description | Inputs | Outputs | Precondition | Postcondition |
|---|---|---|---|---|---|---|
| FR-08 | 6 | Display beverage categories (Coffee, Milk coffee, Tea, Chocolate, ...). | Home screen | Category tabs | Menu configured | Categories displayed |
| FR-09 | 7 | Display the drinks of the selected category, with price and availability badge. | Selected category | Drink cards | Category exists | Drinks displayed |
| FR-10 | NEW | Customise a drink in real time: size, milk type (none/whole/oat/lactose-free), coffee strength (1–5), temperature (warm/hot/extra hot), syrup shots (0–3), extra espresso shot. Price and nutrition update immediately. | Customisation controls | Updated price + nutrition | Drink available | Configuration ready to order or save |
| FR-11 | 11 | Show nutritional information (kcal, sugar, fat, caffeine) and allergens for the **current customised configuration**. | Drink + customisation | Nutrition panel | Nutrition data per ingredient | Information displayed |
| FR-12 | 8 | Prevent selection of beverages whose ingredients (including cups) are depleted or below the per-ingredient minimum threshold. Show the reason. Re-evaluate after every dispense and every refill. | Ingredient levels, thresholds, recipe quantities | Disabled card with reason, e.g. "Out of milk"; order rejected by the server | One or more ingredients are insufficient | Drink cannot be selected or ordered |

### C. Custom recipes

| ID | Lab2 | Description | Inputs | Outputs | Precondition | Postcondition |
|---|---|---|---|---|---|---|
| FR-13 | 4 | Save and name a custom recipe from the current customisation. | Name, base drink, customisation | Recipe shown under "My recipes" | Logged in; name unique for this user | Recipe saved |
| FR-14 | 5 | Modify a saved recipe (name and/or parameters). | Recipe, new values | Updated recipe | Logged in; owner of recipe | Changes saved |
| FR-15 | NEW | Delete a saved recipe. | Recipe | Recipe removed | Logged in; owner | Recipe deleted |
| FR-16 | NEW | One-touch ordering of a saved recipe. | Tap on recipe | Payment screen with the recipe pre-configured | Logged in; base drink available | Order started |

### D. Personalisation and AI

| ID | Lab2 | Description | Inputs | Outputs | Precondition | Postcondition |
|---|---|---|---|---|---|---|
| FR-17 | NEW | Calculate a recommendation score for every drink from **time of day**, **weather data**, **ordering history** and profile preferences. | Clock, weather (API or cached), user history | Score per drink, with a human-readable reason | — (works for guests with time + weather only) | Scores available to the UI |
| FR-18 | NEW | Reorder the menu by score and highlight the top-3 items ("Recommended for you"). | Scores | Sorted, highlighted menu | Scores calculated | Menu reordered |
| FR-19 | 10 | Analyse the user's facial expression with the camera to estimate mood (tired, happy, stressed, neutral) and suggest a tailored recipe, e.g. an extra espresso shot for *tired*. | Camera frame | Mood + tailored suggestion | Camera present; consent given | Suggestion shown |
| FR-20 | NEW | Ask for explicit consent before every camera analysis. Offer a manual mood picker when the user declines or no camera is available. | Consent / manual mood | Analysis starts, or the manual picker | — | — |
| FR-21 | NEW *(optional module)* | Local LLM agent: translate a free-form request ("something sweet with a kick, low on dairy") into explicit machine parameters (drink, milk, strength, syrup, shots). Validate them against availability and show them for confirmation. | Natural-language text | Proposed configuration + explanation | LLM module enabled | User confirms or edits; nothing dispensed without confirmation |

### E. Ordering, payment, transactions and receipts

| ID | Lab2 | Description | Inputs | Outputs | Precondition | Postcondition |
|---|---|---|---|---|---|---|
| FR-22 | NEW | Accept credit/debit cards (EMV chip or contactless). | Card interaction | Approved / declined | Order configured | Payment authorised |
| FR-23 | NEW | Accept mobile digital wallets (Apple Pay, Google Pay). | Wallet tap | Approved / declined | Network & wallet processor available | Payment authorised |
| FR-24 | NEW | Accept internal prepaid employee cards with a stored balance. Reject the payment if the balance is insufficient. | Card UID, amount | New balance, or "insufficient balance" | Card registered | Balance debited |
| FR-25 | NEW | Prepare the drink. Deduct ingredient quantities (beans, milk, water, cocoa, syrup, **cup**), and increase the waste-tank and grounds-bin levels. | Paid order | Drink dispensed | Payment authorised; bins not full; no blocking fault | Inventory and bins updated |
| FR-26 | NEW | Automatically record every completed transaction with all customisation parameters (milk, strength, temperature, syrup shots, size), price, payment method and user. | Completed order | Transaction record | Drink dispensed | Stored; used for history and recommendations |
| FR-27 | 9 | Deliver the receipt as a QR code on screen. | Transaction | QR code | Transaction recorded | Receipt retrievable by scanning |
| FR-28 | 9 | Deliver the receipt by email (pre-filled for logged-in users). | Transaction, email | Email sent, or an error | Valid email | Receipt delivered |
| FR-29 | NEW | Show the user's order history, with re-order. | Session | List of transactions | Logged in | — |

### F. Resilience

| ID | Lab2 | Description | Inputs | Outputs | Precondition | Postcondition |
|---|---|---|---|---|---|---|
| FR-30 | NEW | When the network or an external service (weather API, wallet processor) fails: fall back to basic manual ordering, compute recommendations from local data only, disable wallets, and accept cards **offline** (store-and-forward) and prepaid cards from local balance. Show an "offline mode" banner. | Connectivity status | Degraded but working UI | Network/service failure detected | Offline transactions queued and synced when back online |

### G. Maintenance (secure administrative mode)

| ID | Lab2 | Description | Inputs | Outputs | Precondition | Postcondition |
|---|---|---|---|---|---|---|
| FR-31 | NEW (Lab2: "technician authorized") | Enter secure administrative mode with a physical key, an NFC master card, or a technician PIN. Exit automatically after inactivity. | Key switch / master card UID / PIN | Admin panel, or "access denied" (logged) | — | Admin session active |
| FR-32 | 12 | Register an ingredient refill (milk, beans, cocoa, water, syrup, cups): either add a quantity, or reset the counter to maximum capacity. | Ingredient, quantity or "reset to max" | Updated level | Admin mode | Inventory updated; availability re-evaluated; event logged |
| FR-33 | NEW | Raise a "Low Ingredient Threshold" warning when an ingredient falls below its threshold. | Levels | Warning on dashboard + event log | — | Warning until refilled |
| FR-34 | 13 | Monitor the liquid-waste tank and the coffee-grounds bin. Alert at ≥ 80 %, and **halt operations** at 100 % (overflow). | Bin levels | Status OK / Warning / Full; ordering blocked when full | Bin sensors | Technician alerted |
| FR-35 | NEW | Register the emptying of a bin, which resets it to 0 % and lifts the halt. | Bin | Updated status | Admin mode | Bin reset; event logged |
| FR-36 | 14 | Display real-time error messages ("Grinder Jammed", "Water Heater Fault", "Low Ingredient Threshold", ...) on the admin dashboard, with severity, and allow acknowledging/resolving them. Critical faults block ordering. | Machine error events | Live error list | Admin mode | Errors visible; resolution logged |
| FR-37 | NEW | Store every event (errors, refills, bin emptying, logins, transactions, admin access) in an event log that can be filtered and exported for **remote diagnostics**. | Events | Filterable log; JSON export endpoint | Admin mode | — |

## 1.2 Non-Functional Requirements (all NEW: Assignment 2 had no NFRs)

| ID | Category | Requirement | Measurable acceptance criterion |
|---|---|---|---|
| NFR-01 | Privacy (GDPR) | Facial images are processed entirely in memory and discarded immediately. They are never written to disk or sent over the network. | No image file, DB blob or outbound request is created by mood analysis (code review + test) |
| NFR-02 | Security | Passwords and technician PINs are never stored in plain text. | Salted adaptive hash (PBKDF2/scrypt) |
| NFR-03 | Security | Maintenance functions are only reachable in admin mode. | 100 % of admin endpoints return 403 / redirect without admin mode (automated tests) |
| NFR-04 | Security (payments) | No raw card data (PAN, CVV) is stored. | PCI-DSS: only tokens / masked last-4 digits stored |
| NFR-05 | Availability / resilience | The machine stays usable without network. | All core ordering flows pass with the network disabled |
| NFR-06 | Performance | The UI responds quickly on the embedded hardware. | 95 % of screens render in < 1 s; customisation updates in < 200 ms |
| NFR-07 | Performance | Mood inference is fast. | Camera frame → suggestion in < 2 s on the device |
| NFR-08 | Reliability | Payment, stock deduction and transaction record are atomic. | No partial state after a failure (single DB transaction) |
| NFR-09 | Usability | A standard order is quick. | A guest can order a default drink in ≤ 4 taps; one-touch recipe in 2 taps |
| NFR-10 | Accessibility | The touchscreen is readable and operable. | WCAG 2.1 AA contrast; touch targets ≥ 44 × 44 px |
| NFR-11 | Auditability | Every admin action is traceable. | Refill, bin emptying, fault resolution and admin login are logged with timestamp and actor |
| NFR-12 | Transparency | Recommendations are explainable. | Each recommended item shows the reason, e.g. "Rainy & cold → hot chocolate" |
| NFR-13 | Maintainability | Modular, documented code. | Every function has a docstring (purpose, inputs, outputs); automated tests for core features |
| NFR-14 | Modularity | The LLM agent is an optional plug-in. | The system builds and runs with the LLM module disabled |

## 1.3 LLM suggestions rejected by the team

| ID | Suggestion | Decision |
|---|---|---|
| X-01 | Loyalty programme (points → free drinks) | Rejected (see comparison §4) |
| X-02 | Automatic re-ordering of ingredients from suppliers | Rejected |
| X-03 | Voice ordering through a microphone | Rejected |
| X-04 | Multi-language UI | Rejected (deferred) |
| X-05 | Sales analytics / revenue reports for admins | Rejected (deferred) |
| X-06 | Software-controlled automatic descaling/cleaning cycles | Rejected |
| X-07 | Sharing custom recipes with colleagues / social feed | Rejected |
