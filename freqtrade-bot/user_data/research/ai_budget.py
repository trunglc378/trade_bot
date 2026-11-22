"""Persistent, shared AI quota and per-market cache for local research workers."""
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import logging
import math
import os
import re
from pathlib import Path
import tempfile
import time
from urllib.error import HTTPError
from zoneinfo import ZoneInfo


class AIBudgetUnavailable(RuntimeError):
    pass


@contextmanager
def locked_state(directory, provider):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    lock = (directory / f'{provider}.lock').open('a+b')
    acquired = False
    try:
        lock.seek(0, os.SEEK_END)
        if not lock.tell():
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        acquired = True
        path = directory / f'{provider}.json'
        state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {
            'version': 1, 'day': '', 'requests': 0, 'minute': [],
            'blocked_until': 0, 'next_call': 0, 'cache': {}, 'last_error': None,
        }
        if state.get('version') != 1:
            raise AIBudgetUnavailable('Invalid AI quota state version')
        if (type(state.get('requests')) is not int or state['requests'] < 0
                or not isinstance(state.get('minute'), list)
                or not isinstance(state.get('cache'), dict)):
            raise AIBudgetUnavailable('Invalid AI quota state')
        yield path, state
    finally:
        if acquired:
            lock.seek(0)
            if os.name == 'nt':
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


def save(path, state):
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         delete=False) as output:
            name = output.name
            json.dump(state, output, ensure_ascii=False, allow_nan=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def bounded(settings, key, default, minimum, maximum):
    value = settings.get(key, default)
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'Invalid AI limit {key}')
    return value


def retry_delay(error, now, minimum):
    raw = error.headers.get('Retry-After') if error.headers else None
    if raw:
        try:
            seconds = float(raw)
            return max(minimum, seconds) if math.isfinite(seconds) else minimum
        except ValueError:
            try:
                return max(minimum, parsedate_to_datetime(raw).timestamp() - now)
            except (TypeError, ValueError, OverflowError):
                pass
    return minimum


def advise_with_budget(provider, model, candidates, request, *, directory, scope,
                       settings=None, now=None):
    settings = settings or {}
    now = time.time() if now is None else now
    cooldown = bounded(settings, 'pair_cooldown_seconds', 900, 900, 3600)
    interval = bounded(settings, 'min_interval_seconds', 300, 300, 3600)
    daily = bounded(settings, 'daily_requests', 450, 1, 450)
    rpm = bounded(settings, 'requests_per_minute', 8, 1, 10)
    tpm = bounded(settings, 'tokens_per_minute', 200000, 1, 240000)
    # The other Gemini models in the supplied account have a 20 RPD / 5 RPM tier.
    if provider == 'gemini' and not model.endswith('flash-lite'):
        daily, rpm = min(daily, 18), min(rpm, 4)
    zone = ZoneInfo('America/Los_Angeles') if provider == 'gemini' else timezone.utc
    day = datetime.fromtimestamp(now, zone).date().isoformat()
    context = hashlib.sha256(json.dumps([scope, model], sort_keys=True).encode()).hexdigest()
    keys = {row['pair']: f"{context}:{row['pair']}" for row in candidates}
    with locked_state(directory, provider) as (path, state):
        if day > state['day']:
            state.update(day=day, requests=0)
        if day < state['day']:
            raise AIBudgetUnavailable('Clock moved backwards')
        state['minute'] = [r for r in state['minute'] if now - r['at'] < 60]
        state['cache'] = {k: v for k, v in state['cache'].items() if now < v['expires']}
        votes = {pair: state['cache'][key]['vote'] for pair, key in keys.items()
                 if key in state['cache']}
        pending = [row for row in candidates if row['pair'] not in votes]
        # Bound input at its source. The worker batches the eligible pairs.
        batch = []
        for row in pending:
            if len(json.dumps([*batch, row], ensure_ascii=True).encode()) > 12000:
                break
            batch.append(row)
        # UTF-8/escaped input bytes conservatively bound text tokens, with margin
        # for schema, instructions, framing and the 4k output budget.
        tokens = len(json.dumps(batch, ensure_ascii=True).encode()) + 12000
        allowed = (batch and now >= state['blocked_until'] and now >= state['next_call']
                   and state['requests'] < daily and len(state['minute']) < rpm
                   and tokens + sum(r['tokens'] for r in state['minute']) <= tpm)
        if not allowed:
            save(path, state)
            return votes
        state['requests'] += 1
        state['minute'].append({'at': now, 'tokens': tokens})
        state['next_call'] = now + interval
        save(path, state)  # Charge attempts before sending, including crashes/errors.
        try:
            fresh = request(provider, model, batch)
        except Exception as error:
            status = error.code if isinstance(error, HTTPError) else None
            code = None
            if isinstance(error, HTTPError):
                try:
                    detail = json.loads(error.read(4096))['error']
                    candidate = detail.get('code') or detail.get('status') or detail.get('type')
                    if isinstance(candidate, str) and re.fullmatch(r'[A-Za-z0-9_]{1,80}', candidate):
                        code = candidate
                except (ValueError, TypeError, KeyError, OSError):
                    pass
            delay = 1800 if status in (429, 401, 403, 404) else 900
            state['blocked_until'] = now + retry_delay(error, now, delay) if status else now + delay
            state['last_error'] = {'at': now, 'http_status': status, 'code': code, 'type': type(error).__name__}
            save(path, state)
            logging.getLogger('research').warning('AI provider=%s status=%s code=%s error=%s cooldown_seconds=%s',
                                                  provider, status, code, type(error).__name__,
                                                  state['blocked_until'] - now)
            if isinstance(error, (OSError, TimeoutError)):
                return votes
            raise
        state['last_error'] = None
        # Missing recommendations also receive cooldown and cannot create buy votes.
        for row in batch:
            pair = row['pair']
            if pair not in fresh:
                fresh[pair] = {'action': 'wait', 'confidence': 0, 'reason': 'AI chưa có đánh giá'}
        for pair, vote in fresh.items():
            vote['expires_at'] = datetime.fromtimestamp(now + cooldown, timezone.utc).isoformat()
            state['cache'][keys[pair]] = {'expires': now + cooldown, 'vote': vote}
        save(path, state)
        return {**votes, **fresh}
