"""Durable operator-test accounting; provider quota remains an independent limit.

No prompts, credentials, answers or provider error bodies are retained here.
There is no verified local GPT-OSS tokenizer. Reservations therefore keep the
conservative UTF-8 byte bound and framing allowance, never an E5 token estimate.
"""
import json
from pathlib import Path


class BudgetExceeded(Exception):
    pass


class TestBudgetExceeded(BudgetExceeded):
    pass


class RequestBudget:
    def __init__(self, *, max_tokens=60000, max_requests=18, path=None, identity=None):
        if type(max_tokens) is not int or type(max_requests) is not int or min(max_tokens, max_requests) <= 0:
            raise ValueError('Positive integer test limits required')
        self.path = Path(path) if path is not None else None
        self.identity = identity
        self.max_tokens, self.max_requests = max_tokens, max_requests
        self.entries, self.blocked_reason = [], None
        if self.path is not None and self.path.exists():
            prior = json.loads(self.path.read_text())
            if (prior['max_tokens'], prior['max_requests'], prior['identity']) != (max_tokens, max_requests, identity):
                raise ValueError('Test budget identity/limits changed; preserve the prior run')
            self.entries, self.blocked_reason = prior['entries'], prior['blocked_reason']
            self.summary()  # Reject malformed accounting rather than resetting it.
        elif self.path is not None:
            self.persist()  # A valid zero-request run must also be resumable.

    def summary(self):
        confirmed = estimated = reserved = 0
        for index, entry in enumerate(self.entries):
            if entry['id'] != index or type(entry['reservation']) is not int or entry['reservation'] <= 0:
                raise ValueError('Invalid persisted reservation')
            if entry['state'] == 'confirmed':
                usage = entry['confirmed_usage']
                if type(usage) is not int or usage < 0:
                    raise ValueError('Invalid confirmed usage')
                confirmed += usage
            elif entry['state'] == 'estimated':
                estimated += entry['reservation']
            elif entry['state'] == 'reserved':
                reserved += entry['reservation']
            else:
                raise ValueError('Invalid persisted budget state')
        return {'confirmed_usage': confirmed, 'estimated_usage': estimated,
                'estimated_usage_kind': 'upper_bound_for_requests_without_provider_usage',
                'reserved_budget': reserved,
                'remaining_test_budget': self.max_tokens - confirmed - estimated - reserved,
                'requests_reserved': len(self.entries), 'max_tokens': self.max_tokens,
                'max_requests': self.max_requests, 'blocked_reason': self.blocked_reason,
                'provider_quota_is_separate': True}

    def persist(self):
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            target = self.path.with_suffix(self.path.suffix + '.pending')
            target.write_text(json.dumps({'version': 1, 'identity': self.identity,
                'max_tokens': self.max_tokens, 'max_requests': self.max_requests,
                'blocked_reason': self.blocked_reason, 'entries': self.entries,
                'summary': self.summary()}, indent=2) + '\n')
            target.replace(self.path)

    def reserve(self, request):
        if self.blocked_reason:
            raise TestBudgetExceeded(self.blocked_reason)
        maximum = request.get('max_completion_tokens')
        if type(maximum) is not int or maximum <= 0:
            raise ValueError('Explicit positive max_completion_tokens required')
        wire_bytes = len(json.dumps(request, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode())
        upper_bound = wire_bytes + 4096 + maximum
        remaining = self.summary()['remaining_test_budget']
        if len(self.entries) >= self.max_requests or upper_bound > remaining:
            self.blocked_reason = 'test_request_cap' if len(self.entries) >= self.max_requests else 'test_token_cap'
            self.persist()
            raise TestBudgetExceeded(self.blocked_reason)
        ident = len(self.entries)
        self.entries.append({'id': ident, 'state': 'reserved', 'wire_bytes': wire_bytes,
            'max_completion_tokens': maximum, 'framing_allowance': 4096,
            'reservation': upper_bound, 'confirmed_usage': None})
        self.persist()  # Before network I/O; a crash/resume never frees this reservation.
        return ident

    def settle(self, ident, usage, *, status_code=None, headers=None):
        entry = self.entries[ident]
        if entry['state'] != 'reserved':
            raise ValueError('Request budget already settled')
        reported = usage.get('total_tokens') if isinstance(usage, dict) else None
        entry['http_status'] = status_code
        allowed = {'retry-after', 'x-ratelimit-limit-tokens', 'x-ratelimit-remaining-tokens',
                   'x-ratelimit-reset-tokens', 'x-ratelimit-limit-requests',
                   'x-ratelimit-remaining-requests', 'x-ratelimit-reset-requests'}
        # Numeric/duration headers only, never arbitrary messages or account IDs.
        entry['provider_rate_limits'] = {key.lower(): value for key, value in (headers or {}).items()
            if key.lower() in allowed and len(value) <= 64
            and all(c in '0123456789. smhd' for c in value)}
        if type(reported) is int and reported >= 0:
            entry.update(state='confirmed', confirmed_usage=reported)
            if reported > entry['reservation']:
                self.blocked_reason = 'provider_usage_exceeded_reservation'
                self.persist()
                raise TestBudgetExceeded(self.blocked_reason)
        else:
            entry['state'] = 'estimated'  # Includes 429/400; no assumption of free rejected requests.
        self.persist()
