from datetime import datetime, timezone

import database


def test_normalize_naive_datetime_to_utc():
    value = datetime(2026, 8, 25, 18, 0, 0)
    result = database.normalize_datetime_utc(value)
    assert result.tzinfo == timezone.utc


def test_normalize_aware_datetime_to_utc():
    value = datetime(2026, 8, 25, 18, 0, 0, tzinfo=timezone.utc)
    result = database.normalize_datetime_utc(value)
    assert result == value


def test_neural_projection_is_deterministic_across_calls():
    import api_handler

    first = api_handler._simulate_technical_indicators(3400.12, 0.37)
    second = api_handler._simulate_technical_indicators(3400.12, 0.37)
    assert first == second


def test_neural_projection_seed_does_not_depend_on_python_hash_randomization():
    import hashlib
    import random

    material = b"3400.12:0.3700"
    seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    assert random.Random(seed).random() == random.Random(seed).random()
