"""
Automated Test Suite for PLUTO v2 Agent Core & Reasoning
"""

import os
import sys
import time

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from core.self_learner import get_self_learner
from core.brain import handle_request
from core.knowledge_base import get_knowledge_base

def run_tests():
    learner = get_self_learner()
    kb = get_knowledge_base()

    print("========================================")
    print("PLUTO v2 COMPREHENSIVE TEST SUITE")
    print("========================================")

    # Test 1: User's exact query
    print("\n[TEST 1] Testing user query: 'which is the worst movie by Saif Ali Khan'")
    start = time.time()
    ans1 = learner.answer("which is the worst movie by Saif Ali Khan")
    duration = time.time() - start
    print(f"Response ({duration:.2f}s):\n{ans1}")
    assert len(ans1) > 10, "Response 1 too short"
    assert "LLM placeholder" not in ans1, "Placeholder found in response"
    assert "Superpositions of thermalisations" not in ans1, "Hallucinated quantum physics found in response"
    print("--> TEST 1 PASSED")

    # Test 2: Basic Greeting
    print("\n[TEST 2] Testing basic greeting: 'Hi Pluto'")
    ans2 = learner.answer("Hi Pluto")
    print(f"Response:\n{ans2}")
    assert "hello" in ans2.lower() or "help" in ans2.lower(), "Greeting failed"
    print("--> TEST 2 PASSED")

    # Test 3: Math Evaluation
    print("\n[TEST 3] Testing math: 'calculate 250 * 4'")
    ans3 = learner.answer("calculate 250 * 4")
    print(f"Response:\n{ans3}")
    assert "1000" in ans3, "Math failed"
    print("--> TEST 3 PASSED")

    # Test 4: Concise Fact Query
    print("\n[TEST 4] Testing simple fact: 'Who is the CEO of Tesla?'")
    ans4 = learner.answer("Who is the CEO of Tesla?")
    print(f"Response:\n{ans4}")
    assert "Elon" in ans4 or "Musk" in ans4 or "Tesla" in ans4, "Fact query failed"
    print("--> TEST 4 PASSED")

    # Test 5: Report Generation (PDF + Docx + Markdown)
    print("\n[TEST 5] Testing report generation: 'create a report on Artificial Intelligence trends'")
    start = time.time()
    rep_ans = handle_request("create a report on Artificial Intelligence trends")
    duration = time.time() - start
    print(f"Response ({duration:.2f}s):\n{rep_ans}")
    assert "generated successfully" in rep_ans, "Report generation failed"
    print("--> TEST 5 PASSED")

    # Test 6: Knowledge Base Filtering & Stats
    print("\n[TEST 6] Testing Knowledge Base stats & precision")
    stats = kb.get_stats()
    print(f"KB Stats: {stats}")
    # Verify irrelevant queries return no bad matches
    irrelevant = kb.get_relevant_knowledge("which is the worst movie by Saif Ali Khan")
    print(f"KB direct matches for Saif Ali Khan: {len(irrelevant)} items")
    for item in irrelevant:
        print(f" - Matched: {item.get('title')}")
        assert "thermalisation" not in item.get('title', '').lower(), "Corrupt physics match returned!"
    print("--> TEST 6 PASSED")

    print("\n========================================")
    print("ALL 6 TESTS PASSED SUCCESSFULLY!")
    print("========================================")

if __name__ == "__main__":
    run_tests()
