# 5. Prompt Strategy and Transcript (Appendix)

## 5.1 Model and tooling

| Item | Value |
|---|---|
| Model | **Claude Opus 5.5** (`claude-opus-5-5`, Anthropic; knowledge cutoff June 2026) |
| Interface | Claude Code (desktop app, "Code" tab), agent mode with file read/write tools |
| Used for | Task A (all artifacts + comparison), Task B (complete code generation), Task C (README, docstrings, repository set-up) |
| Date | 25-Oct-2026 (single session) |

## 5.2 What the human actually typed (verbatim inputs, in order)

| # | User input | Note |
|---|---|---|
| U1 | The full text of the *Lab Assignment 3* instructions (Tasks A, B, C) | No additional instruction |
| U2 | The file `Task2b Lab2(G33).docx` (Assignment 2 deliverable) | Sent after the model asked for the System Description |
| U3 | The full *System description for all lab assignments* (SmartBrew AI) | See [`00_system_description.md`](00_system_description.md) |

Everything below was produced by the model from these three inputs. The user
asked for no corrections during generation. The team's review afterwards is
recorded in [`04_comparison.md`](04_comparison.md) (rejections and
modifications).

## 5.3 Prompt strategy

The work was split into a **staged prompt chain** instead of one "write
everything" prompt. **Transparency note:** P1–P5 are the stage instructions
the agent followed inside the session. They are written below as reusable
prompt text so that the process can be replicated in any chat LLM. The user
did not type them as five separate messages (see §5.2). Each stage has one artifact, an explicit role, a fixed
output format, and constraints against hallucination.

| Technique | How it was applied |
|---|---|
| **Role prompting** | "Act as a senior requirements engineer for an IoT/AI coffee machine." |
| **Context grounding** | The System Description is pasted verbatim in every stage. The model must cite which description bullet each requirement comes from. |
| **Format templating** | The Assignment 2 table columns are given explicitly (ID, Description, Inputs, Outputs, Precondition, Postcondition / WHO, WHAT, WHY / ID, Name, Imp, Est, How to demonstrate, Notes). |
| **Decomposition** | One artifact per prompt (P1 requirements → P2 stories → P3 backlog), and each stage gets the previous output, to keep IDs traceable. |
| **Generate, then filter** | The model is asked to add "beyond-the-description" ideas *in a separate list*, so the team can accept or reject them (→ X-01…X-07). |
| **Self-critique** | P4 asks the model to review its own output for gaps, overlaps, untestable wording and invented numbers. |
| **Comparison prompt** | P5 gives both documents and asks for a diff-style comparison plus improvements, misses and errors. A human verified every claim. |

## 5.4 Main prompts and key responses

### P1: Functional and non-functional requirements

```text
Act as a senior requirements engineer. Below is the system description for
"SmartBrew AI", an interactive IoT/AI coffee machine.

<system description pasted verbatim>

Task: elicit the FUNCTIONAL and NON-FUNCTIONAL requirements.
- Functional requirements: one table per functional area, columns
  ID | Description | Inputs | Outputs | Precondition | Postcondition.
  Each requirement must be atomic (one behaviour) and testable.
- Cover EVERY bullet of the description; afterwards print a coverage
  matrix bullet -> requirement IDs.
- Non-functional requirements: ID | Category | Requirement | Measurable
  acceptance criterion. Include the NFRs implied by the description
  (privacy of facial images, offline behaviour).
- When you choose a concrete number (time-out, threshold), mark it as an
  assumed default.
- Put ideas that go BEYOND the description in a separate list
  "Additional suggestions" - do not mix them into the main tables.
```

**Key response (excerpt):** the model returned 37 FRs in groups A–G and 14
NFRs. It marked 5 attempts / 60 s / 80 % / 20 % as assumed defaults and
listed 7 additional suggestions: loyalty, supplier re-ordering, voice,
multi-language, analytics, descaling, recipe sharing. Its coverage matrix
mapped all 18 description bullets.
*Final version:* [`01_requirements.md`](01_requirements.md).

### P2: User stories

```text
Using the requirements from P1, write user stories in the format
ID | WHO ("As a ...") | WHAT ("I want ...") | WHY ("so that ...").
Roles: office user / registered user / guest, technician, administrator.
For each story add condensed acceptance criteria (Given/When/Then) and the
FR IDs it traces to. One story per user goal; avoid stories that bundle
two different mechanisms.
```

**Key response (excerpt):**
> US-12 · As a user · I want the camera to read my mood and suggest a drink ·
> so that I get a drink that fits how I feel · *Consent asked first; tired →
> espresso with extra shot suggested; image never stored* · FR-19, FR-20, NFR-01

*Final version:* [`02_user_stories.md`](02_user_stories.md) (22 stories).

### P3: Product backlog

```text
Create a product backlog from the user stories with the columns
ID | Name | Imp | Est | How to demonstrate | Notes.
Imp: 10-30 (higher = more important), Est: ideal days.
"How to demonstrate" must be a concrete, step-by-step demo that a grader
could follow. Order by importance. Add a column with the story IDs.
```

**Key response (excerpt):**
> PB-04 · Block unavailable drinks · 30 · 3 · *Set milk to 0 in admin mode →
> milk drinks greyed out with "Out of milk"; a direct order request is rejected*

*Final version:* [`03_product_backlog.md`](03_product_backlog.md). The demo
steps were updated after the prototype was built so that they name the real
screens.

### P4: Self-review

```text
Review the three artifacts you produced. List:
(1) description bullets that are not or only partially covered,
(2) duplicates/overlaps between items,
(3) wording that is not testable,
(4) numbers you invented that need stakeholder validation,
(5) open questions/ambiguities to ask the customer.
```

**Key response (excerpt):** it found the overlap PB-16 ↔ PB-10/PB-11 (→ M7)
and listed the invented numbers (→ M1). Open questions it raised: "Is the NFC
login card the same as the prepaid employee card?" (→ M2) and "Where does the
machine get its location for weather data?" (→ M3).

### P5: Comparison with Assignment 2

```text
Here is our Assignment 2 deliverable (user stories, requirements, backlog)
<Lab 2 content> and your artifacts from P1-P3.
Compare them:
- coverage of each system-description bullet (full / partial / missing),
- side-by-side differences in git-diff notation (- human, + LLM),
- what the LLM improved, what it missed or did worse,
- errors or inconsistencies in the human version,
- for each LLM suggestion we might reject, the arguments for and against.
```

**Key response:** the draft of [`04_comparison.md`](04_comparison.md). The
team checked it against the original `.docx` (story numbering, typos, which
requirements have no backlog item) and wrote the final justifications for
the rejections.

## 5.5 Task B: code generation conversation

The prototype was **fully generated** by the same model in the same session.
The only prompt for Task B was the assignment text itself (U1): "Select a core
set of 10 features … realize/code these 10 functionalities with LLM
assistance … ensure a working user experience." The model then worked on its
own:

1. It selected 10 backlog items (★ in the backlog; justification in [`../taskB/feature_selection.md`](../taskB/feature_selection.md)).
2. It chose the stack (Python 3 + Flask + SQLite) because Python was the only runtime installed on the development machine and graders can run it without a build step.
3. It wrote the application, templates, seed data and pytest suite, ran the tests, and fixed failures until all passed.
4. It wrote the README and docstrings (Task C).

The source code in the repository *is* the response. Design decisions the
model made on its own (simulated payment, heuristic mood analysis,
rule-based NL parser) are documented in the README under "Simulated
components".

> A full machine transcript of the session can be exported from Claude Code
> (session menu → *Export transcript*) and attached to the Canvas ZIP if the
> instructor requires the raw conversation.
