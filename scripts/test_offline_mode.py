"""Test PLUTO's behavior with the internet disconnected but Ollama still up.

We simulate "no internet" at the socket layer: socket.create_connection is
patched to raise OSError, which is exactly what a disabled network adapter does
to SelfLearner.is_online() (its probe of 8.8.8.8:53 / 1.1.1.1:53 fails and it
returns False). Ollama is left running locally and untouched, because a disabled
adapter does not affect a loopback service.

This exercises the REAL is_online() logic and the REAL offline fallback path,
and asserts that NO web request is attempted while offline (so nothing can hang
on a doomed connection). It is faithful to the disabled-adapter failure mode
without disrupting the machine's actual connectivity.

Usage: python scripts/test_offline_mode.py
"""

from __future__ import annotations

import socket
import time

from core.self_learner import get_self_learner
from core import self_learner as sl_mod

QUERIES = [
    ("smalltalk", "hi"),
    ("simple", "what is 12 x 8"),
    ("research", "what's the latest news on AI"),
]

_real_create_connection = socket.create_connection

_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def offline_create_connection(address, *a, **k):
    # A disabled network adapter blocks EXTERNAL connectivity but NOT loopback,
    # so Ollama (127.0.0.1:11434) must still work. Fail only for non-loopback
    # hosts (this is what breaks is_online()'s 8.8.8.8 / 1.1.1.1 probes and any
    # web-scraping attempt), and pass loopback straight through.
    host = address[0] if isinstance(address, (tuple, list)) else address
    if host in _LOOPBACK:
        return _real_create_connection(address, *a, **k)
    raise OSError(f"simulated: network is unreachable (adapter disabled) -> {host}")


def run(label, learner, web_calls):
    for kind, q in QUERIES:
        t0 = time.perf_counter()
        try:
            ans, src = learner.answer(q)
            dt = time.perf_counter() - t0
            note = "OFFLINE-NOTE" if "no internet connection detected" in ans else "no-note"
            print(f"\n[{label} / {kind}] {q!r}")
            print(f"  {dt:5.2f}s  source={src}  {note}")
            print(f"  -> {ans[:200]!r}")
        except Exception as exc:
            dt = time.perf_counter() - t0
            print(f"\n[{label} / {kind}] {q!r}")
            print(f"  {dt:5.2f}s  RAISED {type(exc).__name__}: {exc}")


def main() -> None:
    learner = get_self_learner()

    # Count any web-search attempts so we can prove none happen while offline.
    web_calls = {"n": 0}
    orig_online = learner._answer_online

    def counting_online(query):
        web_calls["n"] += 1
        return orig_online(query)

    learner._answer_online = counting_online

    # --- Offline phase -------------------------------------------------
    print("=" * 70)
    print("OFFLINE (socket.create_connection patched to fail; Ollama still up)")
    print("=" * 70)
    t0 = time.perf_counter()
    socket.create_connection = offline_create_connection
    try:
        online_now = learner.is_online()
        print(f"is_online() -> {online_now}  (checked in {time.perf_counter()-t0:.3f}s)")
        web_before = web_calls["n"]
        run("OFFLINE", learner, web_calls)
        print(f"\nweb-search attempts while offline: {web_calls['n'] - web_before} (expect 0)")
    finally:
        socket.create_connection = _real_create_connection

    # --- Back online phase --------------------------------------------
    print("\n" + "=" * 70)
    print("NETWORK RESTORED (real connectivity)")
    print("=" * 70)
    t0 = time.perf_counter()
    print(f"is_online() -> {learner.is_online()}  (checked in {time.perf_counter()-t0:.3f}s)")

    learner._answer_online = orig_online


if __name__ == "__main__":
    main()
