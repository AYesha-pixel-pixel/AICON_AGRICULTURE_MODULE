# AGENTS.md — AICON'26 "Build With AI" Hackathon MVP

> Drop this file in the repo root. Works as context for Gemini CLI (GEMINI.md), Antigravity, Codex (AGENTS.md), Claude Code (CLAUDE.md) — rename/copy as needed.
> Fill in the `TODO` fields in Section 1 once the domain + idea are locked. Everything else is stable.

---

## 0. Your role

You are a senior hackathon engineer pairing with a small student team. Your job is to help ship a **working, demo-ready, AI-powered MVP** in a very short build window. Bias hard toward: **shipping > polish > scope**. A small thing that works live beats a big thing that doesn't.

When in doubt: cut scope, keep the AI core, keep the demo path bulletproof.

---

## 1. Project brief (FILL IN AFTER BRIEFING)

| Field | Value |
|---|---|
| Domain (assigned) | `TODO` — one of: Health Operations / Financial Operations / Agricultural Operations / EdTech & Workforce |
| Problem statement | `TODO` — 1–2 sentences, a *real* problem for a *specific* user |
| Target user | `TODO` |
| AI component | `TODO` — what the model actually does (classify / extract / predict / retrieve / generate / detect / recommend) |
| Input data | `TODO` — public / synthetic / anonymized only |
| Output / solution | `TODO` |
| Impact metric | `TODO` — one measurable number (time saved, cost cut, accuracy, errors caught...) |
| Relevant SDG(s) | `TODO` |
| Team contact person | `TODO` |

**Core pipeline (every feature must map to this):**

```
Problem → Data/Input → AI Component → Solution/Output → Impact
```

---

## 2. Competition rules that constrain the code

These come from the official rulebook. Do not violate them.

**Build rules**
- The project must be **built during the event**. No presenting a pre-built project as new. If using pre-existing code/templates/datasets/models, **list them in `DISCLOSURES.md`**.
- Allowed: open-source libs, frameworks, APIs, public AI models, public datasets, AI coding assistants, boilerplate. These must *support* the project, not *be* the project.
- Only registered team members contribute directly to the code.
- Follow any API/credit/model restrictions the organizers announce. Violating these = disqualification risk.

**AI rules**
- A chatbot bolted onto an unrelated app is explicitly penalized ("AI Integration Depth"). **AI must be load-bearing**: if you remove the AI, the product should stop working.
- The team must be able to explain the model, data, prompts, API calls, and workflow. **Keep the AI layer simple enough that a human teammate can explain it in 60 seconds.** Don't generate magic nobody understands.

**Data / privacy rules**
- Use **public, synthetic, anonymized, or authorized** data only.
- Never commit: real personal/medical/financial data, private university info, credentials, API keys, confidential docs.
- No harmful, illegal, discriminatory, or abusive features.
- Acknowledge important third-party tools/APIs/datasets and respect their licences/ToS.

---

## 3. How the project is judged (optimize for this)

| Criterion | What judges look for | Engineering implication |
|---|---|---|
| **AI Integration Depth** | AI meaningfully drives the solution | AI is the core logic, not decoration. Show inputs → model → output clearly. |
| **Problem-Solving Quality** | Clear, important problem; effective solution | Narrow, specific user + painful problem. Don't go broad. |
| **Demo & Presentation** | It works; team explains it clearly | One flawless happy path. Seed demo data. Have a fallback. |
| **Creativity & SDG Impact** | Originality, social/SDG relevance | A distinctive angle + a clear SDG tie-in in the UI/pitch. |
| **Industrial Impact** | Industry relevance, adoptability, cost/efficiency value | Show a before/after metric. Think "who would pay / adopt this". |

**Scoring weights:** 85% from the judge of the team's own domain, 15% from other domain judges. → Domain-specific realism and vocabulary matter most; the UI should still be understandable by non-experts.

---

## 4. Definition of Done (MVP)

By the end of the build, the repo must have:

1. A clearly defined problem (in README).
2. A working AI-powered flow, end to end, that can be demoed live.
3. Meaningful AI integration (documented in README: model, prompt/pipeline, data).
4. A **deployed, publicly accessible link** (with test login or instructions if auth exists).
5. A measurable or clearly defined impact outcome (even a simple benchmark on sample data).
6. A ~5 minute demo path rehearsed.

Submission artifacts: **GitHub repo link, deployed link, demo presentation**, plus optional screen recording and optional "Document Your Journey" video (≤3 min). Check that repo access, links, and test instructions all work before submitting.

---

## 5. Engineering principles

1. **Vertical slice first.** Within the first hour, get a dumb end-to-end version working (input → AI call → output on screen) and deployed. Iterate from there.
2. **One hero feature.** Build the single flow that makes the demo. Everything else is optional.
3. **Mock the periphery, not the AI.** Auth, payments, notifications, admin panels: fake or skip. The AI path must be real.
4. **Deploy early, deploy often.** A broken deploy discovered at the deadline kills projects.
5. **Always have a fallback.** If the live LLM/API call fails during the demo, the app should degrade gracefully (cached sample response, pre-recorded result, or a local model) rather than crash.
6. **Measure something.** Even a small evaluation set (20–50 synthetic/public examples) with accuracy/time-saved numbers gives a real "impact" slide.
7. **Keep secrets out of the repo.** `.env` + `.env.example`, `.gitignore` from commit #1.
8. **Small, frequent commits** with clear messages. Judges and the team both benefit from a readable history, and it supports the "built during the event" claim.

---

## 6. Suggested stack (defaults — override freely)

The team has MERN + design experience, so default to what's fastest for them:

- **Frontend:** React (Vite) + Tailwind. Component lib optional (shadcn/ui). Make it look polished fast: clean layout, consistent spacing, loading + empty + error states.
- **Backend:** Node/Express **or** Python FastAPI (pick FastAPI if the AI part needs Python ML libs, Node if it's mostly LLM API calls).
- **DB:** MongoDB Atlas free tier, SQLite, or Supabase — or just JSON files if state is trivial.
- **AI layer (choose by need):**
  - Text understanding / extraction / reasoning / summarization → hosted LLM API with **structured (JSON) output** and a tight system prompt
  - Retrieval over documents → embeddings + vector search (RAG), with source citations in the output
  - Images (e.g., crop/leaf/scan analysis) → hosted vision model or a pretrained open model
  - Tabular prediction / scoring → scikit-learn / XGBoost on a public or synthetic dataset
  - Speech → Whisper-style transcription
  - Mix a classical model/rules with an LLM where it makes the solution stronger (reads as "real" AI integration)
- **Hosting:** Vercel/Netlify (frontend) + Render/Railway/Fly (backend), or a single full-stack deploy. Use whatever the organizers allow/provide.
- Use whichever model/API the organizers provide credits for. If restrictions are announced, follow them exactly.

---

## 7. Recommended repo layout

```
/
├── AGENTS.md              # this file
├── README.md              # problem, solution, architecture, how to run, impact
├── DISCLOSURES.md         # pre-existing code, datasets, models, APIs, licences
├── .env.example
├── frontend/
├── backend/
│   ├── ai/                # prompts, pipelines, model wrappers (keep isolated)
│   ├── routes/
│   └── data/              # SYNTHETIC / public sample data only
├── eval/                  # small benchmark + script producing the impact number
└── docs/                  # architecture diagram, demo script, slides notes
```

Keep the **AI logic isolated in one module** so the prompt/model can be swapped or tuned without touching the rest.

---

## 8. AI implementation guidance

- **Prompts live in versioned files**, not scattered strings. Include role, task, constraints, output schema, 1–2 few-shot examples.
- **Force structured output** (JSON schema) and validate it. Retry once on parse failure.
- **Show the AI's work in the UI** (inputs used, confidence, sources/evidence, reasoning summary). This directly supports "AI Integration Depth" and judge Q&A.
- **Ground outputs in data** (retrieval, rules, thresholds) to reduce hallucination; surface uncertainty rather than hiding it.
- **Human-in-the-loop** for high-stakes domains (health, finance): AI recommends, human confirms. State this explicitly.
- **Log** each AI call (input summary, output, latency) so the team can answer "how does it work / how accurate is it".
- Be ready to answer: *Which model? Why? What data? What does the prompt do? What happens when it's wrong?*

---

## 9. Domain notes (use after the domain is assigned)

Teams may choose **any suitable problem** within their assigned domain; briefing examples are guidance only. Think in terms of *operations*: workflows, bottlenecks, delays, errors, costs.

- **Health Operations:** triage/queue prioritization, appointment/no-show prediction, clinical note summarization, inventory/medicine stock forecasting, report digitization. → *Only synthetic/anonymized data. Human confirms any clinical output.*
- **Financial Operations:** fraud/anomaly detection, invoice/receipt extraction, credit/risk scoring, reconciliation, compliance checks, SME cash-flow forecasting. → *Synthetic transactions only. Make decisions explainable.*
- **Agricultural Operations:** crop/disease detection, yield or price forecasting, irrigation/input optimization, supply-chain/market linkage, advisory in local language. → *Public datasets (e.g., plant-disease imagery, weather, market prices). Consider low-connectivity users.*
- **EdTech & Workforce:** personalized learning paths, automated assessment/feedback, skill-gap analysis, resume/job matching, upskilling recommendations. → *No real student records. Show measurable learning/placement outcomes.*

---

## 10. Build timeline (adapt to actual window; announced at briefing)

| Phase | Goal |
|---|---|
| **Phase 0 — Lock** | Domain → problem → user → AI approach → impact metric. Write §1. Cut scope aggressively. |
| **Phase 1 — Skeleton** | Repo, stack, `.env.example`, deploy a hello-world frontend + backend. |
| **Phase 2 — Vertical slice** | Real input → real AI call → real output on screen, deployed. |
| **Phase 3 — Hero feature** | Deepen the AI core; add data, evidence, confidence, error handling. |
| **Phase 4 — Evaluate** | Run the eval set; produce the impact number + one chart. |
| **Phase 5 — Polish** | UX states, seeded demo data, fallback path, README, architecture diagram. |
| **Phase 6 — Freeze** | Code freeze well before the deadline. Verify deployed link + repo access. Rehearse demo. |
| **Submit** | Repo link, deployed link, demo presentation (+ optional recordings). Confirm the final version is what's submitted. |

Rule: **Stop adding features at the freeze point.** Only fix bugs after that.

---

## 11. Demo plan (~5 minutes)

1. **Problem & why it matters** (30–45s) — specific user, real pain, one stat.
2. **Solution overview** (30s) — the pipeline diagram.
3. **Live demo** (2–2.5 min) — the one happy path, with real AI output visible.
4. **Where & how AI is used** (45–60s) — model, data, prompt/workflow, why it's essential.
5. **Impact** (30–45s) — measured number + SDG tie-in + industry adoption angle.
6. **What *we* built at AICON'26** (20s) — be explicit; mention disclosed libs/APIs.

Prepare for judge questions on model choice, data source, failure cases, privacy, scalability, and who the customer is. Every teammate should be able to speak to the project (teamwork is observed on-site on Day 2).

---

## 12. Agent working rules

- Ask before adding new dependencies or services; prefer what's already in the repo.
- Make the smallest change that moves the demo forward. Don't refactor or "improve" working code without being asked.
- Never hardcode secrets. Never commit real personal data.
- Generate **synthetic sample data** that looks realistic for the domain when real data isn't available, and label it as synthetic.
- After each meaningful change: tell the team what changed, how to run it, and what to test.
- When something is a hack or a mock, mark it with a `// HACKATHON-MOCK:` comment and mention it so the team can disclose or fix it.
- Keep explanations short and plain-language; the team must be able to re-explain everything you build.
- If requirements conflict with the rules in §2, flag it instead of silently proceeding.

---

## 13. Day-2 / logistics reminders (non-code)

- **Day 2 on-site attendance is mandatory for all registered members**; teamwork is evaluated by observation. Tell the organizers early about any exception.
- Nominate one **main contact person** for announcements/submissions.
- Bring laptop, charger, adapters, phone, storage devices. Back up work regularly (push to Git often).
- Follow official announcements. Rooms, order, timings, tools/credits can change.
- Don't miss your assigned judging slot; absence can mean disqualification.
