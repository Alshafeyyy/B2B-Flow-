# How the ALX Prospecting Automation Actually Works

This document explains, in full detail and in plain language, exactly what happens between typing in a search (an industry, a country, a size) and getting back a spreadsheet of real companies, real people, and ready-to-send outreach messages. Nothing here is simplified for the sake of being short — it's simplified only in the sense that it avoids technical vocabulary. Every mechanism described below is what the system actually does today.

There are five stages. Each one is explained on its own, and there's a real worked example at the end that walks a single company all the way through.

---

## Stage 1 — Choosing who to look for

The starting point is a real, continuously-updated business directory (Apollo) that holds detailed profiles on companies and the people who work at them — similar in spirit to a very large, very detailed business registry, except it also tracks things like company size, revenue, and what roles a company is currently hiring for.

The search is built from a small number of real filters:

- **Industry** — matched two different ways at once. First, a loose match against the company's general business description (this casts a wide net). Second, an exact match against the directory's own official industry classification for that company. The exact match exists because the loose match alone was found to be unreliable early on — searching for "healthcare," for example, once pulled in a dairy producer and a recruitment agency, because their marketing content happened to mention health-related words in passing. The exact classification match fixes that.
- **Country / location**
- **Company size** (number of employees)
- **Two optional extra filters**, added later because they turned out to be strong signals in their own right:
  - **Revenue range** — a direct read on whether a company has the budget for this kind of investment.
  - **"Currently hiring for…"** — if a company is actively hiring for roles like "data analyst" or "AI engineer" right now, that's real, current evidence they're already investing in exactly what ALX sells — a much sharper signal than industry or size alone.
- **A list of companies to exclude** — so a repeat search next month doesn't waste time re-surfacing companies already found before.

**The most important thing to understand about the number you enter is what it actually counts.** It is not "how many companies to look at" — it's "how many *qualified* companies to find." The system will keep looking at more and more real companies from the directory, one at a time, until it has found that many genuine "Go" companies (see Stage 2) — or until it has honestly exhausted a reasonable amount of searching (it will look at up to five times the number requested before giving up and telling you plainly how many it actually found). This matters because industries vary a lot in how many companies turn out to be a good fit — asking for 5 "Go" companies in a niche sector might mean quietly checking 20 real companies behind the scenes to find them.

---

## Stage 2 — Deciding Go, Review, or No-Go

This is where the AI does its first real piece of judgment, and it's worth explaining thoroughly because this is the step that determines everything downstream.

For every single company found in Stage 1, the AI is given two things: everything known about that specific company (its industry, size, location, and public description), and a detailed, structured description of what ALX actually is and who it actually serves — pulled directly from ALX's own market positioning materials, not written generically. That second part contains several real pieces of ALX's own research:

**Eight organizational warning signs.** These are not something written for this system — they are lifted directly, word for word and number for number, from ALX's own B2B brand presentation (slide 4, "Les défis sont interconnectés" / "The challenges are interconnected"), which presents them as a bubble chart with the note: *"Data from global surveys of executives and HR leaders, 2024-2025."* That slide itself footnotes each individual figure to a named outside research report:

| Signal | How common it is | Original source (as footnoted in ALX's own deck) |
|---|---|---|
| Adopting AI without a real governance plan | 78% | McKinsey & Company, *The State of AI 2025* |
| Managers not ready to lead their teams through change | 70% | Gallup, *State of the Global Workplace 2024* |
| A visible skills gap in the workforce | 63% | World Economic Forum, *Future of Jobs Report 2025* |
| Resistance to change inside the organization | 60% | Gartner, *Top 5 Priorities for HR Leaders 2025* |
| Teams struggling with productivity | 57% | Microsoft, *Work Trend Index 2024* |
| Limited capacity to innovate | 52% | Deloitte, *Global Human Capital Trends 2024* |
| Trouble retaining talent | 51% | LinkedIn, *Workplace Learning Report 2025* |
| Decisions being made without real data | under 33% | NewVantage Partners, *Data & AI Leadership Survey 2024* |

In other words: nothing here was invented or estimated for this system. It's ALX's own market research, already vetted and used with real clients — which is exactly why it was used as the qualification criteria instead of writing new logic from scratch. The AI is instructed to look for genuine, visible evidence of two or more of these signals — not to assume them. It is also explicitly told two things to keep it from being lazy or biased in either direction:

1. **Don't require a specific news story about that exact company.** Most companies never publish anything about their internal training or digital initiatives — that silence is normal, not a red flag. If a company is a real, established player in a sector where ALX's own research already shows strong, credible pressure (banking is a named example — Bank Al-Maghrib itself has publicly stated that digital and AI modernization is a priority for the sector), that sector-wide evidence is treated as real evidence on its own.
2. **Don't default to "yes" just because a company is large, or "no" just because an industry sounds traditional.** ALX has real, proven placements across banking, telecom, retail, technology, and pharmaceutical-adjacent companies alike — so the sector itself is never used as a shortcut in either direction.

Every company gets sorted into exactly one of three outcomes, always with a short, specific, human-readable reason attached — not a generic sentence:

- **Go** — real evidence of the signals above, or being a genuine, established company in a sector ALX's research already covers.
- **Review** — a plausible fit, right size and sector, but the evidence is genuinely unclear either way. Meant for a person to look at, not to be acted on automatically.
- **No-Go** — clear evidence this isn't a fit, most commonly a company far too small to realistically have any structured training budget or process.

All three outcomes are recorded — not just the winners. That matters, because it means nothing is hidden: you can always see every company that was checked and exactly why it was or wasn't chosen.

At the same time, for any company marked Go or Review, the AI also suggests which kinds of roles are worth targeting there — not by guessing generic job titles, but by connecting the specific evidence it found to the specific parts of what ALX offers. For example, evidence of ungoverned AI adoption points toward targeting digital or transformation leaders; evidence of manager readiness gaps points toward HR and frontline management; evidence of weak data-driven decisions points toward senior financial or operational leadership.

*(A note on why this matters: an earlier version of this logic was too strict — it required a specific news article about each individual company before it would say "Go," which meant almost everything came back "Review" even for obviously strong prospects like real, established banks. That was found through direct testing and corrected — sector-level evidence, backed by ALX's own real research, is now explicitly enough on its own for an established company. This is a live system that gets tested against real companies and corrected when something isn't working as intended.)*

---

## Stage 3 — Finding the right people inside each company

This stage only runs for companies that came back "Go." For each one, two things happen in sequence.

**First**, the system pulls the real, complete list of people the business directory has on file at that company — their first names and job titles, nothing else yet. Not a guess at what roles *should* exist there — the actual roster of real people, whatever their real titles happen to be.

This two-step approach (look at everyone first, decide who to contact second) replaced an earlier, more direct method that tried to search the directory for people matching AI-guessed job titles like "Chief Human Resources Officer" directly. That approach failed constantly, because most real companies don't have anyone with that exact title — a company's actual HR lead is far more often titled something like "Regional HR Manager" or "Talent Acquisition Manager." Searching for the guessed title returned nothing, and the system would fall back to picking essentially random senior people — a CEO, a Communications Director — regardless of whether they had anything to do with training or HR. Pulling the real, full list first and then choosing from *that* fixed the problem entirely, because there's no guessing left to get wrong.

**Second**, the AI reviews that real list — often 50 to 100 real people — and picks a small handful (typically up to five) who are the best fit. It does this by matching each real job title against a second piece of ALX's real material: the actual structure of what ALX sells, broken down by who each part is actually built for —

- A self-paced online learning platform, covering AI, data analytics, and leadership topics, generally relevant to a broad range of employees.
- Six specific in-person workshops, each with a stated real audience — for example, one is built for operational and support staff doing high-volume day-to-day work, another is built specifically for executives and transformation leaders, another for frontline managers, another for the senior executive committee.
- A six-month leadership development program aimed at managers and rising leaders.

The AI is told to prioritize genuine decision-makers and real functional fits over generic seniority, and for every person it picks, it writes down a short, specific reason why. That reason is kept and shown in the final results — so it's never a mystery why a given person was chosen.

---

## Stage 4 — Unlocking real contact details

Only the small number of people the AI actually picked in Stage 3 have their full details unlocked — a verified email address, phone number, and LinkedIn profile, pulled from the business directory's deeper records. Everyone else on that original 50-to-100-person list is left alone.

This is deliberate: unlocking full contact details has a real cost each time, so it only happens for people who were actually going to be contacted, never for the rest of the list just because they were reviewed.

It's normal, and not a sign of anything wrong, if a small number of these picked people still come back without a verified email — not every real person has one on record. When that happens, it's clearly marked rather than hidden or guessed at.

---

## Stage 5 — Writing the personalized outreach message

This is the final and most detailed step, run once for each unlocked contact. Here, the AI is given everything known about that specific person (their name, title, and public profile) and the company, plus the same detailed ALX positioning material used earlier — but this time used differently.

Two things from ALX's own material are used specifically to shape the *tone* and *substance* of the message:

**Two real buyer patterns**, drawn from ALX's own account of who actually engages with this kind of offer:

- A **senior, time-pressed, results-first** pattern (internally referred to as the "Karim" type, after a real client persona in ALX's own materials) — typically an operations or functional executive, and usually the actual budget holder. For someone matching this pattern, the AI is told to lead with efficiency and a fast, concrete payoff, and to skip generic "upskilling" language entirely.
- A **curious, hands-on, growth-first** pattern (the "Youssef" type) — typically a specialist or individual contributor, not the budget holder, but a genuine internal advocate. For this pattern, the AI leads with practical skill-building and career growth instead.

The AI first judges which pattern a given contact more closely resembles based on their real title and role, and writes accordingly — so a Director of Operations and a Data Analyst at the same company will receive two genuinely different opening messages, not the same message with the name swapped in.

**Real proof points**, so nothing written is a generic, unverifiable claim — for example, ALX's real client count (470+ corporate clients, 3,000+ enterprise learners trained), specific named companies where ALX-trained people have since been hired or promoted (Orange Maroc, Sophatel, Veeva Systems, Carrefour Maroc), the fact that ALX provides a dedicated local team and a named point of contact rather than a purely remote, self-serve platform, and ALX's strategic partnership with the Mastercard Foundation.

The AI is instructed to name a specific real ALX offering (an actual workshop or program, not "our training") and cite one specific real proof point in the opening message — not a vague claim.

What comes out for each contact is four connected pieces of writing:

1. **Background on the person** — their real role, tenure, and responsibilities, based on genuine research into their public profile.
2. **The opening pitch** — the persona-matched, proof-point-backed message described above.
3. **A brief on the company** — connecting the company's scale and situation specifically to whichever of the eight signals from Stage 2 was actually found for them.
4. **Where the industry stands** — how this company's sector compares to others in adopting AI and digital tools, for context.

---

## What comes out the other end

One spreadsheet, two tabs:

- **Every company that was checked**, Go, Review, or No-Go alike, each with its reason — the complete picture, not just the successes.
- **Every contact that was found and unlocked**, with their verified details, the reason they were picked, and their full four-part written brief, ready to hand to a salesperson.

---

## Why this can be trusted

- **Nothing is hidden.** Every company checked is recorded, not just the ones that passed. Every contact selection and every "Go" decision comes with a specific, readable reason, not a black-box score.
- **Nothing is wasted.** Contact details are only unlocked for people who were actually chosen. Companies that clearly don't fit are skipped before any deeper research is spent on them.
- **Nothing is lost.** Progress is saved continuously — after every single company checked and every single contact written up — so an interruption partway through never costs the work already done.
- **It's been tested against real problems, not just built once.** The role-matching approach, the qualification strictness, and the search filters described here were all refined after being run against real Moroccan companies and found to have real, specific problems — which were then fixed and re-verified against those same companies.

---

## A real worked example

To make the above concrete, here is what actually happened in one real test run, start to finish.

**The search:** banking companies in Morocco.

**Stage 2, qualification:** CIH Bank came back **Go**, with the AI's actual reason recorded as:
> *"CIH Bank is a real, established Moroccan bank, and banking is a sector under strong AI/digital transformation and data-upskilling pressure aligned with ALX Enterprise's AI, data, and workforce productivity offerings."*

**Stage 3, finding people:** at a different real "Go" company in the same test (Sothema, a pharmaceutical company), the full people list came back with around 100 real names and titles. The AI picked five, with reasons including:
> *"Group CHRO — as Group CHRO, she is a top decision-maker for workforce upskilling and learning initiatives."*
> *"Directeur Digital — as Directeur Digital, he is a strong sponsor for AI, data, and digital transformation training."*

**Stage 5, writing the pitch:** for a Director of Operations, the AI recognized the senior, ROI-first pattern and opened with:
> *"...as Director of Operations, he is more likely to respond to a concise ROI and execution message than to generic upskilling language. A strong opener would be: ALX Africa's AI Strategic Roadmap workshop can help identify where AI is already reducing workload..."*

For a Data Analyst at the same company, it recognized the growth-first pattern instead and opened with:
> *"...a functional specialist/individual contributor who is likely to value practical skill-building and career growth over executive-level ROI messaging... ALX Africa's Decision Intelligence workshop could help your analytics team..."*

Same company, same offering, two different real people — two genuinely different messages, each grounded in something real about ALX and something real about the person receiving it.
