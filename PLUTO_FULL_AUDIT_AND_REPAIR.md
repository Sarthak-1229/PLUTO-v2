## PLUTO v2 — Full System Audit & Repair

Paste everything below into Claude Code as one task. Do not skip Phase A —
fixing before measuring is exactly how the project got here.

---

```
PLUTO v2 has accumulated problems: it's slow, the UI has stale/broken
elements from multiple past redesigns, it's unclear whether the knowledge
base actually persists and gets reused, answers are sometimes vague, and
there's no visibility into whether an answer came from the local model or
from a web search. Work through this in four phases, in order. Do not
implement fixes before Phase A is complete and reported.

## PHASE A — Audit (measure everything, fix nothing yet)

Write scripts/audit.py that runs a battery of real requests against the
live system (server must be running) and records, for each:
- Total wall-clock latency, broken down by stage if possible (STT time,
  classification time, search time, LLM generation time, TTS time) — add
  timing instrumentation at each stage in the actual request path if it
  doesn't already exist, don't estimate.
- Which path was taken: smalltalk / simple / research / KB-cache-hit
- Whether a new knowledge_db.json entry was created (compare entry count
  before and after)
- The raw response text (to manually assess vagueness/quality)

Test battery (minimum, add more if useful):
1. "hi" (smalltalk)
2. "what is 15% of 340" (simple/computable)
3. "who is the current CEO of Nvidia" (research — needs current info)
4. Send the SAME research question twice in a row — second call should be
   faster and should indicate it used cached/KB knowledge, not a fresh
   search
5. A genuinely ambiguous question that could go either way, e.g. "explain
   how binary search works" (model likely knows this — should NOT trigger
   web research)
6. A deliberately vague-prone question, e.g. "tell me about machine
   learning" — check if the response is generic filler or has concrete
   specifics

Also audit the UI: open ui/index.html (or whichever file app.py actually
serves — check for multiple UI files/versions in the repo first, since
past commits show at least three UI redesigns; identify which one is live
and flag any others as dead code) and click through every visible control
(tabs, Voice Mode, Knowledge Bank, Research Reports, Settings). For each,
report: does it do what it visually claims, or is it a dead/non-functional
UI element left over from an earlier version?

Produce audit_report.md with all findings before touching any code. Include
raw timing numbers, not vague descriptions like "seems slow."

## PHASE B — Root cause diagnosis

Based on audit_report.md, diagnose the actual cause of each reported
problem. Specifically check these known-likely culprits from the project's
history and confirm or rule out each one explicitly in the report:
- Is classify_query() making a separate LLM call before the main answer
  call for ambiguous queries (i.e., two sequential heavy model calls per
  request instead of one)?
- Is conversation history being resent uncapped, growing prompt size and
  generation time turn over turn?
- Is the "simple" path still accidentally falling through to the full
  multi-source research pipeline in some cases?
- Are the 8 research sources queried sequentially (blocking) rather than
  in parallel, adding up latency even when only 1-2 sources actually
  return anything useful?
- Is Ollama's keep_alive causing the model to unload between requests,
  forcing a reload (multi-second cold start) on every single message?
- Does the knowledge base actually get read from on repeat queries, or is
  every query treated as novel regardless of KB contents?

## PHASE C — Fix, with a transparency feature required

Implement fixes for whatever Phase B actually confirmed — don't fix
hypothetical problems that Phase A/B didn't find evidence for. In addition,
implement this regardless of audit findings, since it directly addresses
"unable to understand if the answer is from the internet or local model":

Add an explicit `answer_source` field to every /process response:
one of "local_model", "web_research", "knowledge_base_cache". Display this
as a small visible badge/label above each assistant response in the UI
(e.g. "🌐 Web research" / "🧠 Local knowledge" / "💾 From memory"). This
is not optional — it's the direct fix for the source-confusion complaint.

For the UI: remove or clearly disable any dead controls identified in
Phase A rather than leaving non-functional buttons. Consolidate to a
single UI file if multiple stale versions exist in the repo — delete the
others (after confirming with git log which is actually served).

For vagueness: if Phase A's test battery showed generic/filler answers,
revise the LLM system prompt to explicitly require concrete
specifics (numbers, named examples, actual steps) over generic
restatement, and re-test the same battery to confirm improvement.

For speed: address whichever of the Phase B culprits were confirmed.
Reasonable targets: smalltalk/simple answers under 3s, research answers
under 15s (network-dependent, but no unnecessary sequential blocking).

## PHASE D — Re-verify

Re-run scripts/audit.py (same test battery) after fixes. Report before/after
numbers side by side — not just "should be faster now."

## PHASE E — Report

Output in this exact format:

### Phase A findings
- Latency breakdown per test case (before)
- UI audit: which controls work, which are dead
- KB behavior: did repeat queries hit the cache? entry count changes?

### Phase B diagnosis
- For each of the 6 known-likely culprits listed above: confirmed or ruled
  out, with evidence

### Phase C changes
- List of files changed and what specifically was fixed
- Confirm answer_source badge is implemented and visible

### Phase D results
- Same latency test battery, after fixes, side by side with before numbers
- Vagueness test re-run: is "tell me about machine learning" more specific
  now?

### Remaining known issues
- Anything NOT fixed, with why (e.g. inherent hardware limit, needs a
  design decision from the user, out of scope for this pass)

### Commits
- Do NOT commit automatically. List what you would commit and wait for
  explicit confirmation, per the Git Discipline rule in CLAUDE.md.
```
