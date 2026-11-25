"""Persistent worker-wide AI limits. No secrets/prompts are stored in the audit DB."""
import hashlib
import json
from pathlib import Path
import random
import sqlite3
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "strategies"))
from vn_support import in_session

DEFAULTS = {"enabled": False, "only_in_session": True, "min_interval_seconds": 1800,
            "max_requests_per_hour": 2, "max_requests_per_day": 20,
            "cache_ttl_seconds": 600, "max_candidates": 3, "max_input_chars": 12000,
            "backoff_seconds": 900, "max_backoff_seconds": 21600}


class AICallBlocked(RuntimeError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


class AIController:
    def __init__(self, config, directory, advisor, clock=time.time):
        self.config, self.advisor, self.clock = config, advisor, clock
        self.policy = {**DEFAULTS, **config["vn_policy"]["research"].get("ai_control", {})}
        if set(self.policy) - set(DEFAULTS):
            raise ValueError("Unknown AI control option")
        for key in ("enabled", "only_in_session"):
            if type(self.policy[key]) is not bool:
                raise ValueError("Invalid AI control flag")
        for key in set(DEFAULTS) - {"enabled", "only_in_session"}:
            if type(self.policy[key]) is not int or self.policy[key] <= 0:
                raise ValueError("Invalid AI control limit")
        if self.policy["cache_ttl_seconds"] > 600 or self.policy["max_candidates"] > 10:
            raise ValueError("AI freshness/input limits too large")
        self.path = Path(directory) / "ai-control.sqlite"

    @contextmanager
    def _db(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=5)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY, provider TEXT NOT NULL, ts REAL NOT NULL,
                outcome TEXT NOT NULL, code INTEGER);
            CREATE TABLE IF NOT EXISTS state (
                provider TEXT PRIMARY KEY, next_at REAL NOT NULL DEFAULT 0,
                failures INTEGER NOT NULL DEFAULT 0, circuit TEXT,
                cache_key TEXT, cached_at REAL, votes TEXT);
        ''')
        try:
            with db:
                yield db
        finally:
            db.close()

    def __call__(self, provider, specification, candidates):
        p, now = self.policy, self.clock()
        if (self.path.parent / "AI_PAUSE").exists():
            raise AICallBlocked("ai_paused")
        if not p["enabled"]:
            raise AICallBlocked("ai_disabled")
        if p["only_in_session"] and not in_session(datetime.fromtimestamp(now, timezone.utc), self.config["vn_policy"]["schedule"]):
            raise AICallBlocked("outside_ai_session")
        # Rank and bound the entire batch; never call separately for every coin.
        candidates = sorted(candidates, key=lambda r: r.get("score", 0), reverse=True)[:p["max_candidates"]]
        if not candidates:
            return {}
        if len(json.dumps(candidates, ensure_ascii=False, allow_nan=False)) > p["max_input_chars"]:
            raise AICallBlocked("input_limit")
        key = hashlib.sha256(json.dumps({"specification": specification,
            "pairs": sorted(r["pair"] for r in candidates)}, sort_keys=True).encode()).hexdigest()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT OR IGNORE INTO state(provider) VALUES (?)", (provider,))
            state = db.execute("SELECT next_at, failures, circuit, cache_key, cached_at, votes FROM state WHERE provider=?", (provider,)).fetchone()
            next_at, failures, circuit, old_key, cached_at, cache = state
            if circuit:
                raise AICallBlocked("circuit_open_" + circuit)
            if old_key == key and cached_at is not None and 0 <= now - cached_at < p["cache_ttl_seconds"] and cache:
                votes = json.loads(cache)
                for vote in votes.values():
                    vote["from_cache"] = True
                return votes
            if now < next_at:
                raise AICallBlocked("cooldown")
            # Shared rolling windows cover ALL providers/processes using this same DB.
            for seconds, limit, reason in ((3600, p["max_requests_per_hour"], "hourly_limit"),
                                           (86400, p["max_requests_per_day"], "daily_limit")):
                count = db.execute("SELECT count(*) FROM attempts WHERE ts>?", (now - seconds,)).fetchone()[0]
                if count >= limit:
                    raise AICallBlocked(reason)
            cursor = db.execute("INSERT INTO attempts(provider,ts,outcome) VALUES (?,?,?)", (provider, now, "reserved"))
            attempt_id = cursor.lastrowid
            db.execute("UPDATE state SET next_at=? WHERE provider=?", (now + p["min_interval_seconds"], provider))
        try:
            votes = self.advisor(provider, specification, candidates)
            for vote in votes.values():
                vote["analysis_generated_at"] = datetime.fromtimestamp(now, timezone.utc).isoformat()
                vote["from_cache"] = False
            with self._db() as db:
                db.execute("UPDATE attempts SET outcome='success' WHERE id=?", (attempt_id,))
                db.execute("UPDATE state SET failures=0,cache_key=?,cached_at=?,votes=? WHERE provider=?",
                           (key, now, json.dumps(votes, ensure_ascii=False, allow_nan=False), provider))
            return votes
        except Exception as exc:
            code = exc.code if isinstance(exc, HTTPError) else None
            # Auth/payment/unknown-model failures require deliberate operator intervention.
            circuit = str(code) if code in (400, 401, 402, 403, 404) else None
            wait = min(p["max_backoff_seconds"], p["backoff_seconds"] * 2 ** min(failures, 10))
            if isinstance(exc, HTTPError):
                try:
                    wait = max(wait, min(86400, int(exc.headers.get("Retry-After", "0"))))
                except (ValueError, TypeError, AttributeError):
                    pass
            wait += random.uniform(0, 30)
            with self._db() as db:
                db.execute("UPDATE attempts SET outcome='error',code=? WHERE id=?", (code, attempt_id))
                db.execute("UPDATE state SET failures=failures+1,next_at=?,circuit=?,votes=NULL WHERE provider=?",
                           (now + max(wait, p["min_interval_seconds"]), circuit, provider))
            raise


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Inspect AI worker counters or reset a latched circuit; never calls AI")
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--reset-circuit", choices=("gemini", "openai"))
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--pause", action="store_true")
    action.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.pause:
        args.directory.mkdir(parents=True, exist_ok=True)
        (args.directory / "AI_PAUSE").touch()
    if args.resume:
        (args.directory / "AI_PAUSE").unlink(missing_ok=True)
    path = args.directory / "ai-control.sqlite"
    if not path.is_file():
        print(json.dumps({"status": "no_local_audit_db", "paused": (args.directory / "AI_PAUSE").exists()}))
        return
    with sqlite3.connect(path) as db:
        if args.reset_circuit:
            # Preserve usage counters, cache and next_at: reset cannot bypass caps/backoff.
            db.execute("UPDATE state SET circuit=NULL WHERE provider=?", (args.reset_circuit,))
        states = db.execute("SELECT provider,next_at,failures,circuit FROM state").fetchall()
        usage = db.execute("SELECT provider,outcome,code,count(*) FROM attempts WHERE ts>? GROUP BY provider,outcome,code", (time.time() - 86400,)).fetchall()
        print(json.dumps({"usage_rolling_24h": usage, "states": states,
                          "paused": (args.directory / "AI_PAUSE").exists()}, indent=2))


if __name__ == "__main__":
    main()
