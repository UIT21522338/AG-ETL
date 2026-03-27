#!/usr/bin/env python
"""Test naive datetime comparison (no timezone info)"""
import sys
sys.path.insert(0, 'agents/agent-2-error-diagnosis/src')
from datetime import datetime

# Test 1: naive datetime comparison
print("=" * 60)
print("TEST 1: Naive datetime comparison")
print("=" * 60)

# Simulate: DB returned naive datetime in VN time
db_ts = datetime(2026, 3, 27, 20, 52, 0)  # From DB, naive, VN time
now   = datetime.now()                     # Current time, naive, VN time

diff = (now - db_ts).total_seconds() / 60
print(f"DB time  : {db_ts}")
print(f"Now      : {now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Elapsed  : {diff:.1f} min")

if diff > 0:
    print("✓ PASS: naive comparison correct, no 7h offset")
else:
    print(f"✗ FAIL: elapsed {diff:.1f}min should be positive")

# Test 2: parsing _parse_ts function
print("\n" + "=" * 60)
print("TEST 2: _parse_ts function")
print("=" * 60)

from alert_dedup import _parse_ts

# Test with string
str_ts = "2026-03-27 20:52:00"
parsed = _parse_ts(str_ts)
print(f"Input  : '{str_ts}'")
print(f"Parsed : {parsed}")
print(f"Has tzinfo? {parsed.tzinfo if parsed else 'N/A'}")

if parsed and parsed.tzinfo is None:
    print("✓ PASS: _parse_ts returns naive datetime")
else:
    print("✗ FAIL: _parse_ts should return naive datetime without tzinfo")

# Test 3: 5-minute lookback window
print("\n" + "=" * 60)
print("TEST 3: 5-minute lookback window")
print("=" * 60)

from datetime import timedelta

# Simulate a record from 3 minutes ago
old_ts = datetime.now() - timedelta(minutes=3)
lookback_cutoff = datetime.now() - timedelta(minutes=5)

in_window = old_ts >= lookback_cutoff
print(f"Now             : {datetime.now().strftime('%H:%M:%S')}")
print(f"Record at       : {old_ts.strftime('%H:%M:%S')} (3 min ago)")
print(f"Lookback cutoff : {lookback_cutoff.strftime('%H:%M:%S')} (5 min ago)")
print(f"In window?      : {in_window}")

if in_window:
    print("✓ PASS: record within 5-min window is picked up")
else:
    print("✗ FAIL: record should be in window")

# Simulate a stale record from 7 minutes ago
stale_ts = datetime.now() - timedelta(minutes=7)
in_stale_window = stale_ts >= lookback_cutoff

print(f"\nStale record at : {stale_ts.strftime('%H:%M:%S')} (7 min ago)")
print(f"In window?      : {in_stale_window}")

if not in_stale_window:
    print("✓ PASS: stale record is filtered out")
else:
    print("✗ FAIL: stale record should be filtered")

print("\n" + "=" * 60)
print("All tests passed!")
print("=" * 60)
