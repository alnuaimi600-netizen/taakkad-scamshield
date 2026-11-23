# تأكّد | Ta'akkad — Verify Before You Act

**SCAMSHIELD AI Hackathon** (Abu Dhabi Police × 42 Abu Dhabi, November 2026).

> **بالعربي باختصار:** «تأكّد» تطبيق ويب تلصق فيه رسالة واتساب أو SMS مشبوهة (أو ترفع لقطة شاشة)، فيحجب بياناتك الحساسة أولاً، ثم يفحص النص والرابط **بدون فتح الرابط**، ويعطيك واحدة من ثلاث حالات: **اشتباه عالٍ / غير واضح / لا مؤشرات ظاهرة** (لا يقول «آمن» أبداً)، مع ثلاثة أسباب كحد أقصى بلغة بسيطة، وخطوة آمنة، وبلاغ جاهز تنسخه وترسله بنفسك عبر منصة eCrime في تطبيق وزارة الداخلية.

---

## 1. Problem & Solution | المشكلة والحل

**Problem.** People across the UAE, of every age, receive WhatsApp and SMS messages that impersonate shipping companies ("your parcel is held, pay AED 5") or act as buyers on marketplace ads ("I paid you, enter your card here to receive the money"). The message looks routine, the link looks close enough, and the pressure to act fast does the rest. Most people have no quick way to ask "is this normal?" before they tap.

**Solution.** Ta'akkad is a mobile-first web app:

1. **Choose language** (Arabic / English, full RTL/LTR) → **privacy page once** (always reachable from the header).
2. **Input:** paste the text (main path), attach a **screenshot** (OCR runs *in the browser*; the image never leaves the device), or **voice** (optional, browser Web Speech API).
3. **Check:** sensitive data is **masked first**, then the link is checked **as text only** and the wording is checked for warning signs.
4. **Result:** one of three states, up to **3 plain-language reasons**, the triggering words/links **highlighted**, what we checked and what we can't guarantee.
5. **Safe action + "Report the link":** a ready-made report (link, masked text, time received, channel, "what happened?") with a **Copy** button and directions to the **federal eCrime platform in the MOI UAE app**. If the user says they entered card details or paid, the first thing shown is **"Contact your bank right now"**.

| State | When | Suggested action |
|---|---|---|
| `high_suspicion` | Strong signals: link doesn't match the claimed organisation, card/OTP request, pressure | Don't tap, don't pay, report |
| `unclear` | Few or mixed signals | Check with the organisation yourself, via its own app or website |
| `no_visible_indicators` | Nothing found — **this does not mean safe** | Best to open the organisation's app yourself |

### The authority side: linking the public and the security authority | الربط بين الجمهور والجهة الأمنية

The public app never files reports for people. The person still sends the report through **eCrime in the MOI UAE app**. What connects the public to the authority is a **staff dashboard** (`/admin`) built on **anonymous, aggregate** data:

```
Public (Ta'akkad app)                                    Security authority (/admin)
  each check ──► anonymous counters only ──────────────►  indicators: results per day, top fraud
                 (result, signal types, claimed org,       techniques, most-impersonated organisations,
                  domain of non-official links)            recurring suspicious domains
  warning banner on the check screen  ◄───── publish ───  public warnings (AR/EN)
  verdict "high suspicion" + reason   ◄───── confirm ───  confirm a domain as fraudulent
  report text ──► person files it in MOI app eCrime ────►  existing eCrime process (unchanged)
```

- **Early warning:** staff see a campaign forming (for example, many people checking courier-fee messages that lead to one domain) before reports pile up.
- **Two-way:** a domain staff confirm makes every later message containing it `high_suspicion`, with the reason "confirmed by the security authority". Published warnings appear to every user. Shortener services and official domains can't be confirmed, so legitimate links are never blocked by mistake.
- **What's stored per check:** date + hour, result, channel, UI language, signal codes, the claimed organisation/category, and the registered domain of non-official links. **Never stored:** message text (masked or not), numbers, IP address, device info, or anything linking two checks to one person. Tested in `backend/tests/test_dashboard.py`. Stats can be switched off with `TAAKKAD_STATS=0`.
- **Access:** a bearer token (`TAAKKAD_ADMIN_TOKEN`; if unset, a random one is printed to the server console on each start). A real deployment would use the authority's own single sign-on and audit log.
- **Demo data:** `backend/scripts/seed_demo_stats.py` replays the 60 synthetic messages over 14 days so the dashboard has something to show. Every such row is marked synthetic, and the dashboard says so on screen. These are **not** real reports or real volumes.
- **Later, with an official partnership:** direct, consented submission to eCrime with a case number returned. Not built, because it needs an agreement and an API from the Ministry of Interior.

### Product rules that the code enforces
1. The app **never says "safe"** — only the three states above (`backend/app/scoring.py`, tested in `test_verdicts.py`).
2. **Masking before anything else** — cards (Luhn), Emirates ID `784-…`, UAE IBAN `AE..`, phone numbers, e-mails and delivered codes (`backend/app/masking.py`).
3. **Any request for a card number or an OTP ⇒ `high_suspicion`, even if the link is official.** A message that *delivers* a code and says "don't share it" is **not** suspicious.
4. **Links are never fetched by the server.** `url_checks.py` contains no network code (hackathon rules + SSRF risk).
5. The app **does not submit reports** for the user. It prepares the text and points to the official channel.
6. **Nothing is stored by default**; images never leave the device; server logs contain no message text.

---

## 2. Technical Choices | الخيارات التقنية

### Architecture

```
Browser (React + Vite)                         Server (Python + FastAPI)
┌──────────────────────────────┐   masked?    ┌──────────────────────────────────────────┐
│ language → privacy → input   │  no: raw     │ 1. masking.py     cards/EID/IBAN/phones   │
│ screenshot → tesseract.js    │  text, but   │ 2. url_checks.py  text-only link checks   │
│   (OCR on device)            │  masked as   │ 3. text_signals.py AR/EN rules            │
│ voice → Web Speech API       │  step 1 on   │ 4. llm.py (optional) masked text only     │
│ result + highlights          │  the server  │ 5. scoring.py     3 states, ≤3 reasons    │
│ report → copy → MOI eCrime   │ ───────────► │ 6. report.py      ready-to-paste report   │
└──────────────────────────────┘              └──────────────────────────────────────────┘
                                         data/official_domains.json (entities + domains)
```

- **Rules engine first, LLM second.** The rules (`url_checks.py`, `text_signals.py`, `scoring.py`) work fully offline and give deterministic, explainable reasons. They decide the state on their own. The optional LLM layer (`llm.py`) receives **only masked text** plus the rule signals, may **add** signals and write a short plain-language summary, but can **never lower** a rule-based verdict. Any failure (no key, network, refusal, invalid JSON) silently falls back to rules only. It is **off by default** (`TAAKKAD_LLM=1` to enable) because we still need the organisers to confirm external APIs are allowed.
- **Why Claude via API for the LLM layer:** strong Arabic and English, structured JSON output (schema-validated), and no model to host during a hackathon. We use `claude-opus-5-5` at low effort (configurable with `TAAKKAD_LLM_MODEL`) with server-side fallback on refusals.
- **Text-only link checks:** real domain vs. the organisation named in the text; look-alikes (swapped/doubled letters, digit-for-letter like `falc0n`); brand inside another domain (`brand.other-site.test`, `brand-pay.test`); punycode/non-ASCII; URL shorteners; raw IP address; unusual TLDs; `@` tricks; no HTTPS; unusually long/complex links.
- **Arabic handling:** Arabic-Indic digits are normalised before masking; Arabic spelling variants (أ/إ/آ, ة/ه, ى/ي, diacritics, tatweel) are folded for matching; highlights are mapped back to the exact words the user sees.
- **On-device OCR (tesseract.js, `ara+eng`):** privacy over accuracy — screenshots can contain names, numbers and chats, so they never leave the phone. The OCR bundle is lazy-loaded only when the user attaches an image.
- **React + Vite / FastAPI:** small, well-known stacks the whole team can work on in 3 days; FastAPI gives typed request validation (length limits, enums) for free. In production mode FastAPI also serves the built frontend, so there is one origin and one process.

### Alternatives we weighed and excluded

| Option | Why not (for now) |
|---|---|
| Local open-weight LLM | Better privacy, but weaker Arabic intent understanding at sizes we can run, and heavy to set up and demo within the hackathon. Top item for "more time". |
| Classic ML classifier (e.g. TF-IDF + logistic regression) | Needs a large, labelled, real-world dataset we don't have (and must not collect real messages). Also gives no human-readable reasons. |
| Fetching / rendering the link on the server | Forbidden by the hackathon rules (no testing real fraud sites) and a classic SSRF risk. Excluded entirely. |
| Reputation APIs (Google Safe Browsing, PhishTank) | Sends user links to third parties and needs keys/terms review. Planned, not in the prototype. |
| LLM-only verdict | Non-deterministic and could "talk itself" into reassurance. We keep the LLM additive only. |
| Confidence percentage / naming the scam type | Spec decision: a number invites false certainty, and naming types adds no safety value for the user. |
| Accounts / history | Not needed for the task and conflicts with data minimisation. |

### What we'd do with more time
- A **local model** for higher privacy (no external API at all), evaluated against the rules + API setup.
- **Reputation databases** and **sandboxed link analysis** run by an authority, not by the user's request path.
- **Direct report submission** through an official partnership (today the app only prepares the report).
- Dashboard hardening: the authority's single sign-on, roles (viewer / publisher), an audit log of confirmations and warnings, and minimum-count thresholds before showing rare categories.
- A **verified official-domain list** maintained with the relevant authorities, with dates and sources.
- A **held-out evaluation set** written by people who did not write the rules, and the **user study** below.
- Better OCR on WhatsApp screenshots (cropping, chat-bubble detection) and Emirati-dialect voice input.
- Rate limiting, CSP headers and deployment hardening.

### Privacy mechanism | آلية حماية الخصوصية
- **Data minimisation:** only the message text. No name, ID, account or login.
- **Mask first:** `analyse_message()` calls `mask()` before anything else; every later step (rules, LLM, report, opt-in storage) only sees masked text. Tested in `test_masking.py` and `test_api.py`.
- **Anonymous statistics for the authority:** counts and signal types only, never text or identity (see "The authority side" above). Stated on the privacy page.
- **No link fetching**, **no message text in logs** (uvicorn access log = method, path, status), `Cache-Control: no-store` on API responses, errors never echo request content.
- **Images stay on device** (in-browser OCR). Voice uses the browser's speech API, which may process audio externally — stated on the privacy page.
- **Optional, explicit storage:** only if the user ticks the box for that check, the **masked** text and the result are appended to `backend/storage/opt_in.jsonl` (git-ignored). Off by default.
- **Report:** prepared from masked text and re-masked on the server; the user sends it themselves.
- **Legal framework:** the exact UAE data-protection text to cite still needs verification before we quote it.

### Third-party libraries & services

| Component | Use | License |
|---|---|---|
| [FastAPI](https://github.com/fastapi/fastapi) | API server | MIT |
| [Uvicorn](https://github.com/encode/uvicorn) | ASGI server | BSD-3-Clause |
| [Pydantic](https://github.com/pydantic/pydantic) (via FastAPI) | request validation | MIT |
| [anthropic](https://github.com/anthropics/anthropic-sdk-python) | optional LLM client | MIT |
| [pytest](https://github.com/pytest-dev/pytest), [httpx](https://github.com/encode/httpx) | tests | MIT, BSD-3-Clause |
| [React](https://github.com/facebook/react) | UI | MIT |
| [Vite](https://github.com/vitejs/vite), [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react) | build tooling | MIT |
| [tesseract.js](https://github.com/naptha/tesseract.js) (+ Tesseract OCR engine and `ara`/`eng` language data, downloaded by the library at first use) | on-device OCR | Apache-2.0 |
| Claude API (Anthropic) | optional external LLM service | Anthropic commercial terms |
| Browser Web Speech API | optional voice input | browser feature |

All code in this repository is original work by the team.

**Organisers' logos and colours.** `frontend/public/partners/` holds the Abu Dhabi Police and 42 Abu Dhabi logos. They are shown only as hackathon credit (start screen and footer), next to the line "This is not an official Abu Dhabi Police app". The logos belong to their owners. The current files were cropped from the event material; we'll replace them with official, clearer copies from the organisers. The UI palette takes its cues from the logos: charcoal from 42 for the header and main buttons, police red `#B40C24` used **only** for the high-suspicion state and the header stripe (so red always means "warning"), and the falcon's bronze for focus, highlights and links.

**Development tooling (not part of the app).** We used two Apache-2.0 Claude Code skills from [anthropics/skills](https://github.com/anthropics/skills) while building: `frontend-design` (visual design guidance) and `webapp-testing` (Playwright testing of the local app). They are installed locally under `.claude/skills/` and are not shipped with the product.

---

## 3. Build & Run | البناء والتشغيل

**Requirements:** Python 3.12+, Node.js 20+ (tested with Python 3.12.10 and Node 26 on Windows 11).

### Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pytest                                   # 60 tests
uvicorn app.main:app --port 8000         # API on http://127.0.0.1:8000 (docs at /api/docs)
```

### Authority dashboard (staff)
```bash
# optional: fill the dashboard with clearly-labelled synthetic demo data
backend/.venv/Scripts/python backend/scripts/seed_demo_stats.py      # --clear removes demo rows only
# optional: fix the token instead of a random one per run
export TAAKKAD_ADMIN_TOKEN=choose-a-long-random-value                # PowerShell: $env:TAAKKAD_ADMIN_TOKEN="..."
```
Open `http://127.0.0.1:8000/admin` (or `http://localhost:5173/admin` in dev) and sign in with the token (printed in the server console if you didn't set one). Data lives in `backend/storage/taakkad.db` (SQLite, git-ignored).

### Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api to :8000)
# or, single-origin: npm run build  → then open http://127.0.0.1:8000 (FastAPI serves frontend/dist)
```

### Optional: LLM layer
```bash
pip install -r requirements-llm.txt   # Windows: if you get a long-path error, clone into a short folder like C:\taakkad
export ANTHROPIC_API_KEY=...        # Windows PowerShell: $env:ANTHROPIC_API_KEY="..."
export TAAKKAD_LLM=1                # off unless set
# optional: export TAAKKAD_LLM_MODEL=claude-opus-5-5
```

### Evaluation
```bash
backend/.venv/Scripts/python eval/run_eval.py        # macOS/Linux: backend/.venv/bin/python
```
Writes `eval/results.md` and `eval/results.json`.

### Repository layout
```
backend/app/     masking, url_checks, text_signals, scoring, llm, report, analyzer,
                 stats (anonymous aggregates, alerts, confirmed domains), main (FastAPI)
backend/scripts/ seed_demo_stats.py (synthetic demo data for the dashboard)
backend/tests/   60 pytest tests (masking, link checks, verdict rules, API/privacy, dashboard)
frontend/src/    App.jsx (public app), Admin.jsx (staff dashboard at /admin),
                 i18n.js / adminI18n.js (AR/EN), ocr.js, voice.js, styles.css
data/            official_domains.json (UNVERIFIED real entries + fictional .test demo entities),
                 synthetic_messages.jsonl (60 synthetic messages)
eval/            run_eval.py, results.md, results.json
docs/            spec.md (decisions), hackathon-terms.md, deck, mockup
```

---

## 4. Evaluation | القياس

### Technical test (measured)
Run on 23 Nov 2026, **rules only**, 60 synthetic messages (30 scam incl. 12 that ask for card/OTP, 14 legitimate, 8 code-delivery, 8 ambiguous; Arabic and English; WhatsApp and SMS). Full per-message table in [`eval/results.md`](eval/results.md).

| Metric | Result |
|---|---|
| False alarms: benign (legit + code-delivery) rated `high_suspicion` | 1/22 (5%) |
| Misses: scam rated `no_visible_indicators` | 0/30 (0%) |
| Card/OTP requests rated `high_suspicion` | 12/12 (100%) |
| Code-delivery messages rated `high_suspicion` | 1/8 (12%) |
| `unclear` rate (all messages) | 3/60 (5%) |

**Read this honestly:** the same team wrote the rules and the messages, so this is an **in-sample** check that the rules do what we designed, **not** a measure of real-world accuracy. The one false alarm (`o07`, a courier "delivery PIN — give it to the courier" message) is a real limitation of keyword rules: "give the code" can be normal for delivery PINs. We left it as measured rather than tuning rules to the test set.

### User study (designed, not yet run)
60 participants of different ages, randomly split: (A) uses Ta'akkad, (B) reads a standard awareness tip. Each sees 10 synthetic messages (6 fraudulent, 4 legitimate). Measures: safe-action rate, decision time, false alarms, clarity of explanation (1–5), and card/OTP-request detection. **We will not simulate participants with AI and present them as human results.** If not run in time, it is presented as the next step.

---

## 5. Still needs verification | يحتاج تحقق
- **Official-domain list** (`data/official_domains.json`): real entries were typed from general knowledge and are marked `"verified": false`. The app tells the user this whenever it relies on one. Each must be checked against official sources and dated.
- **Report channel:** federal eCrime in the MOI UAE app. Source page checked 21 Nov 2026: <https://u.ae/en/information-and-services/justice-safety-and-the-law/cyber-safety-and-digital-security/report-cybercrimes-online>. The exact in-app form and any deep link still need verification.
- Whether external API services are allowed (affects the LLM layer only).
- OCR quality on real-looking WhatsApp screenshots.

## Safety & data rules followed
- All test and demo links use reserved `.test` / `.example` domains; nothing is ever fetched.
- All messages are synthetic; no real people's messages or numbers.
- Fictional demo organisations (Falcon Express, Oasis Bank, Najm Telecom, Souq Al Waha) are used for legitimate-message examples so no real organisation's systems are involved.
