"""Deterministic tests for the repetition-loop fix:
  - classify_query() routes creative/long-form requests to the "creative"
    category (so they get the large bounded budget, not the simple ceiling)
  - _clip_runaway_repetition() truncates degenerate filler loops while leaving
    legitimate structured content (skits with repeated speaker labels) intact

No LLM required. Run: python scripts/test_repetition_guard.py
"""
from __future__ import annotations
from collections import Counter
from core.self_learner import SelfLearner

cq = SelfLearner.classify_query
clip = SelfLearner._clip_runaway_repetition

class _Stub:  # classify_query only reads its text arg
    pass

pass_n = fail_n = 0
def check(name, cond):
    global pass_n, fail_n
    print(('PASS ' if cond else 'FAIL ') + name)
    pass_n += cond; fail_n += (not cond)

# --- classification ----------------------------------------------------
CLASS = {
    'create a skit about the Trojan War': 'creative',
    'write a short story about a robot': 'creative',
    'compose a poem about the ocean': 'creative',
    'write an essay explaining the water cycle': 'creative',
    'tell me a joke': 'creative',
    'write a rap about gravity': 'creative',
    'hi': 'smalltalk',
    'what is 12 x 8': 'simple',
    'what is the square root of 144': 'simple',
    'who is the current CEO of Nvidia': 'research',
    'tell me about machine learning': 'research',
    'explain how binary search works': 'research',
}
for q, exp in CLASS.items():
    check(f'classify {q!r} -> {exp}', cq(_Stub(), q) == exp)

# --- runaway clipper ---------------------------------------------------
good = 'ACHILLES: We sail at dawn.\nHECTOR: Troy will not fall.\nNarrator: The war begins.'
runaway = good + ('\n\nLet me know if you want more! 🚀' * 50)
check('clips trailing filler loop', clip(runaway) == good)

skit = '\n'.join(['Narrator: Once upon a time in Troy.', 'ACHILLES: I fight for glory.',
                  'HECTOR: I fight for home.', 'ACHILLES: Then we clash.',
                  'Narrator: And so it began.'])
check('leaves legit skit untouched', clip(skit) == skit)

loop = ('Intro line that is long enough here.\n'
        + 'The exact same filler sentence repeats now.\n' * 3).rstrip()
check('clips at first duplicate', clip(loop) == 'Intro line that is long enough here.')

allloop = ('This whole thing is a repeated filler line.\n' * 5).rstrip()
check('all-loop returned as-is (not nuked)', clip(allloop) == allloop)

prose = 'Machine learning is a field of AI.\nIt learns from data.\nExamples include SVM and random forests.'
check('normal prose unchanged', clip(prose) == prose)

print(f'\n{pass_n} passed, {fail_n} failed')
raise SystemExit(1 if fail_n else 0)
