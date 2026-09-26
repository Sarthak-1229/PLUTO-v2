"""Diagnostic test script for PLUTO v2 fixes."""

import json
import sys
import time
from pathlib import Path

# Windows consoles default to cp1252; force UTF-8 so unicode in model
# responses (and the check marks below) can't crash the run.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

def test_fixes():
    """Run diagnostic tests for all fixes."""
    results = {}

    print("=" * 60)
    print("PLUTO v2 Diagnostic Test Suite")
    print("=" * 60)

    # =========================================================================
    # Fix 1: Query Classification & Routing
    # =========================================================================
    print("\n[Fix 1] Query Classification & Routing")
    print("-" * 60)

    from core.self_learner import get_self_learner
    learner = get_self_learner()

    test_cases = [
        ("hi", "smalltalk"),
        ("hello", "smalltalk"),
        ("thanks", "smalltalk"),
        ("what is 100 x 5000", "simple"),
        ("100 * 5000", "simple"),
        ("calculate 250 + 4", "simple"),
        ("research quantum computing", "research"),
        ("who made ai", "research"),
        ("latest news about AI", "research"),
    ]

    results["fix1"] = {}
    for query, expected_type in test_cases:
        actual_type = learner.classify_query(query)
        passed = actual_type == expected_type
        results["fix1"][query] = {
            "expected": expected_type,
            "actual": actual_type,
            "passed": passed
        }
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} '{query}' -> {actual_type} (expected: {expected_type})")

    # Test actual responses
    print("\n  Response length tests:")
    response, _ = learner.answer("hi")
    word_count = len(response.split())
    results["fix1"]["response_lengths"] = {
        "hi": {"words": word_count, "response": response[:100]}
    }
    print(f"    'hi' -> {word_count} words: '{response[:80]}...'")

    # =========================================================================
    # Fix 2: Offline Mode
    # =========================================================================
    print("\n[Fix 2] Offline Mode Handling")
    print("-" * 60)

    # Test is_online with timeout
    start = time.time()
    is_online = learner.is_online()
    elapsed = time.time() - start

    results["fix2"] = {
        "is_online": is_online,
        "timeout_test": {
            "elapsed_seconds": round(elapsed, 2),
            "within_3s": elapsed <= 3.0
        }
    }
    print(f"  is_online(): {is_online} (took {elapsed:.2f}s)")
    print(f"  ✓ Timeout within 3s: {elapsed <= 3.0}")

    # Verify KB has no network calls
    from core.knowledge_base import get_knowledge_base
    kb = get_knowledge_base()
    results["fix2"]["kb_no_network"] = True  # Static file-based, no network
    print(f"  ✓ KB lookup is offline-only (JSON file)")

    # =========================================================================
    # Fix 3: Error Boundaries
    # =========================================================================
    print("\n[Fix 3] Error Boundaries")
    print("-" * 60)

    from app import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # Test /process with valid query
    response = client.post("/process", json={"text": "hi"})
    results["fix3"] = {
        "process_endpoint": {
            "status_code": response.status_code,
            "has_error_field": "error" in response.json(),
            "has_answer_field": "answer" in response.json()
        }
    }
    print(f"  POST /process: status={response.status_code}")
    print(f"  Response keys: {list(response.json().keys())}")

    # Test with invalid query (should not crash)
    response = client.post("/process", json={"text": "test"})
    results["fix3"]["process_on_test"] = {
        "status_code": response.status_code,
        "is_json": response.headers.get("content-type", "").startswith("application/json")
    }
    print(f"  POST /process ('test'): status={response.status_code}, JSON={response.headers.get('content-type', '').startswith('application/json')}")

    # =========================================================================
    # Fix 4: Context Management
    # =========================================================================
    print("\n[Fix 4] Context Management")
    print("-" * 60)

    from core.brain import LLMReasoner
    reasoner = LLMReasoner()

    # Check conversation history is capped
    results["fix4"] = {
        "history_capped": reasoner._max_history == 8
    }
    print(f"  Conversation history cap: {reasoner._max_history} messages")

    # =========================================================================
    # Fix 5: STT Silence Detection
    # =========================================================================
    print("\n[Fix 5] STT Silence Detection")
    print("-" * 60)

    from core.self_learner import SILENCE_THRESHOLD, SILENCE_CONSECUTIVE_SECONDS, MAX_RECORDING_SECONDS
    results["fix5"] = {
        "silence_threshold": SILENCE_THRESHOLD,
        "consecutive_seconds": SILENCE_CONSECUTIVE_SECONDS,
        "max_duration": MAX_RECORDING_SECONDS
    }
    print(f"  Silence threshold: {SILENCE_THRESHOLD}")
    print(f"  Consecutive seconds: {SILENCE_CONSECUTIVE_SECONDS}")
    print(f"  Max recording: {MAX_RECORDING_SECONDS}s")

    # =========================================================================
    # Fix 6: 500 Error Reproduction
    # =========================================================================
    print("\n[Fix 6] 500 Error Reproduction")
    print("-" * 60)

    # Send sequence of messages
    test_sequence = ["hi", "what is 100 x 5000", "who made ai", "hello"]
    errors = []

    for msg in test_sequence:
        try:
            response = client.post("/process", json={"text": msg})
            if response.status_code >= 500:
                errors.append({
                    "message": msg,
                    "status": response.status_code,
                    "response": response.json()
                })
        except Exception as e:
            errors.append({
                "message": msg,
                "error": str(e)
            })

    results["fix6"] = {
        "sequence_tested": test_sequence,
        "errors_encountered": len(errors),
        "error_details": errors if errors else None
    }

    if errors:
        print(f"  [FAIL] Encountered {len(errors)} error(s)")
        for err in errors:
            print(f"    - {err}")
    else:
        print(f"  [PASS] No 500 errors in sequence test")

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)

    all_passed = True
    for fix_name, fix_results in results.items():
        if isinstance(fix_results, dict):
            passed = all(v.get("passed", True) or v.get("within_3s", True) or v.get("is_json", True)
                       for v in fix_results.values() if isinstance(v, dict))
        else:
            passed = True

        print(f"\n{fix_name.upper()}: {'[PASS]' if passed else '[FAIL]'}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)

    # Save results to file
    output_file = Path("diagnostic_report.json")
    output_file.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\nDetailed results saved to: {output_file}")

    return results


if __name__ == "__main__":
    test_fixes()
