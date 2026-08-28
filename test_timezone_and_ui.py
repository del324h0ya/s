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
