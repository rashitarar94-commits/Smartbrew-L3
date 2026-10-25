# 2. User Stories (LLM-generated)

Model: Claude Opus 5.5 · Prompt: P2 in [`05_prompt_log.md`](05_prompt_log.md)

Same WHO / WHAT / WHY format as Assignment 2. The LLM added two columns:
**Acceptance criteria** (Given/When/Then, condensed) and **FR**, which traces
each story to [`01_requirements.md`](01_requirements.md). *Lab2* gives the
matching Assignment 2 story ID (Lab2 had stories 1–7 and 9–11; there is no
story 8).

| ID | Lab2 | WHO | WHAT | WHY | Acceptance criteria | FR |
|---|---|---|---|---|---|---|
| US-01 | 1 | As an office user | I want to create an account and log in with my credentials | so that my preferences, recipes and history are kept | Valid data → account created; duplicate email → error; wrong password → generic error; 5 failures → 5-min lock | FR-01, FR-02 |
| US-02 | 1 | As a registered user | I want to link my NFC badge and log in by tapping it | so that I can start ordering without typing | Linked card tap → logged in < 1 s; unknown card → "unknown card" | FR-03, FR-04 |
| US-03 | — | As a registered user | I want to store default milk type, strength, temperature and dietary flags in my profile | so that every drink starts the way I like it | Saved defaults pre-fill the customiser; the lactose-free flag hides dairy suggestions | FR-06 |
| US-04 | — | As a user on a shared machine | I want to be logged out automatically when I walk away | so that colleagues cannot order on my account | 60 s without interaction → logged out | FR-05 |
| US-05 | 3 | As a user | I want to browse drink categories | so that I can quickly find a drink | Tap category → only its drinks shown, with price | FR-08, FR-09 |
| US-06 | — | As a user | I want to customise milk type, strength, temperature, syrup shots and size and see the price instantly | so that the drink matches my taste and budget | Every change updates price and nutrition without reload | FR-10 |
| US-07 | 7 | As a health-conscious user | I want to see calories, sugar, fat, caffeine and allergens for my exact configuration | so that I can respect my dietary needs | Adding oat milk / syrup changes the shown values; allergens listed | FR-11 |
| US-08 | 4 | As a user | I want drinks that cannot be made to be disabled with a reason | so that I never pay for a drink the machine cannot prepare | Milk below threshold → all milk drinks disabled with "Out of milk"; the server also rejects the order | FR-12 |
| US-09 | 2 | As a registered user | I want to save, name, edit and delete custom recipes | so that I can reuse my favourite configurations | Saved recipe appears in "My recipes"; edits persist; delete removes it; duplicate name → error | FR-13–FR-15 |
| US-10 | — | As a registered user | I want to order a saved recipe with one touch | so that my daily coffee takes seconds | Tap recipe → payment screen pre-filled | FR-16 |
| US-11 | — | As a user | I want the menu to put drinks that fit the time of day, the weather and my history first | so that I find a good choice faster | Morning + history of cappuccinos → cappuccino ranked high; top-3 highlighted with reason | FR-17, FR-18 |
| US-12 | 6 | As a user | I want the camera to read my mood and suggest a drink | so that I get a drink that fits how I feel | Consent asked first; *tired* → espresso with an extra shot suggested; the image is never stored | FR-19, FR-20, NFR-01 |
| US-13 | — | As a user | I want to describe my drink in my own words | so that I don't have to navigate menus | "sweet with a kick, low on dairy" → proposal (e.g. Americano + 2 syrup + extra shot, oat milk) to confirm | FR-21 |
| US-14 | — | As a user | I want to pay with my bank card, phone wallet or employee prepaid card | so that checkout is touchless and convenient | Each method works; insufficient prepaid balance → declined; no card data stored | FR-22–FR-24 |
| US-15 | 5 | As a user | I want to get my receipt by QR code or email | so that I can keep a record of my purchase or expense it | QR shown and scannable; email delivered to the given address | FR-27, FR-28 |
| US-16 | — | As a registered user | I want to see my past orders | so that I can re-order or track spending | History shows date, drink, customisation, price | FR-26, FR-29 |
| US-17 | — | As a user | I want the machine to keep working when the network is down | so that I still get my coffee | Network off → offline banner; manual menu; card accepted offline; wallets disabled | FR-30 |
| US-18 | — | As a technician | I want to enter admin mode with a key, master card or PIN | so that only maintenance staff can change the machine | Wrong PIN → denied and logged; correct → admin panel | FR-31 |
| US-19 | 9 | As a technician | I want to register refills and reset counters to maximum capacity | so that stock levels stay accurate | Reset milk → 100 %; disabled milk drinks become available again | FR-32 |
| US-20 | 10 | As a technician | I want alerts when the waste tank or grounds bin must be emptied, and the machine to halt when they are full | so that nothing overflows | ≥ 80 % → warning; 100 % → ordering blocked; "emptied" → reset and resumed | FR-34, FR-35 |
| US-21 | — | As a technician | I want low-ingredient warnings | so that I can refill before drinks become unavailable | Ingredient < threshold → "Low Ingredient Threshold" event | FR-33 |
| US-22 | 11 | As an administrator | I want real-time error messages on the dashboard and an event log I can export | so that I can diagnose problems remotely | "Grinder Jammed" appears within 5 s; resolving it is logged; log can be filtered and exported as JSON | FR-36, FR-37 |
