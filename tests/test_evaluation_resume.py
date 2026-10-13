from scripts.resume_evaluation import full_turn_cooldown


def test_recovery_includes_actual_draft_consumption():
    # Actual S05 telemetry: the draft succeeded before the verifier hit TPD.
    # Merely waiting 836s would repeatedly fund a draft, then starve verification.
    quota = {'scope': 'TPD', 'limit': 200000, 'used': 198434, 'requested': 3500}
    failures = [{'result': {'token_usage': 3483}}]
    assert full_turn_cooldown(836, quota, failures) == 2342


def test_first_request_quota_wait_is_not_artificially_extended():
    quota = {'scope': 'TPD', 'limit': 200000, 'used': 200000, 'requested': 3500}
    assert full_turn_cooldown(1512, quota, [{'result': {'token_usage': 0}}]) == 1512


def test_does_not_infer_daily_recovery_from_minute_or_missing_telemetry():
    failure = [{'result': {'token_usage': 3483}}]
    assert full_turn_cooldown(60, {'scope': 'TPM', 'limit': 8000, 'used': 7980, 'requested': 3500}, failure) == 60
    assert full_turn_cooldown(60, {}, failure) == 60
