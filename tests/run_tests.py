"""Run unit/integration/browser checks and save reproducible local evidence."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def category(test):
    name = test.id()
    if any(s in name for s in ("PolicyTests.", "ProviderTests.")):
        return "unit"
    if "GroundingTests." in name:
        return "integration" if name.endswith("test_gemini_only_overlay_and_worker") else "unit"
    if "test_vn_policy." in name:
        return "integration" if any(s in name for s in ("multi_ai_consensus", "mock_server")) else "unit"
    return "integration"


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
    def startTest(self, test):
        self.started = time.monotonic()
        self.current_status, self.detail = "PASS", None
        super().startTest(test)
    def addError(self, test, err):
        self.current_status, self.detail = "ERROR", self._exc_info_to_string(err, test)
        super().addError(test, err)
    def addFailure(self, test, err):
        self.current_status, self.detail = "FAIL", self._exc_info_to_string(err, test)
        super().addFailure(test, err)
    def addSkip(self, test, reason):
        self.current_status, self.detail = "SKIP", reason
        super().addSkip(test, reason)
    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.current_status, self.detail = "FAIL", self._exc_info_to_string(err, test)
        super().addSubTest(test, subtest, err)
    def stopTest(self, test):
        self.records.append({"id": test.id(), "status": self.current_status,
                             "duration_seconds": round(time.monotonic() - self.started, 6), "detail": self.detail})
        super().stopTest(test)


def junit(records, target):
    suite = ET.Element("testsuite", name="python", tests=str(len(records)),
                       failures=str(sum(r["status"] in ("FAIL", "ERROR") for r in records)),
                       skipped=str(sum(r["status"] == "SKIP" for r in records)))
    for row in records:
        case = ET.SubElement(suite, "testcase", name=row["id"], time=str(row["duration_seconds"]))
        if row["status"] in ("FAIL", "ERROR"):
            ET.SubElement(case, "failure", message=row["status"]).text = row["detail"]
        if row["status"] == "SKIP":
            ET.SubElement(case, "skipped", message=row["detail"])
    ET.ElementTree(suite).write(target, encoding="utf-8", xml_declaration=True)


def command(name, argv, folder, timeout=30, failure_status="FAIL", env=None):
    start = time.monotonic()
    try:
        proc = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
        output = proc.stdout + proc.stderr
        status, code = ("PASS" if proc.returncode == 0 else failure_status), proc.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        output, status, code = type(exc).__name__ + ": " + str(exc), failure_status, None
    (folder / (name + ".log")).write_text(output, encoding="utf-8")
    return {"id": name, "command": argv, "status": status, "exit_code": code,
            "duration_seconds": round(time.monotonic() - start, 3), "log": name + ".log"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    started = datetime.now(timezone.utc)
    folder = args.output or ROOT / "test-results" / started.strftime("%Y%m%dT%H%M%SZ")
    folder = folder.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    suites = {"unit": [], "integration": []}
    for location in (ROOT / "tests", ROOT / "freqtrade-bot/tests"):
        for test in flatten(unittest.TestLoader().discover(str(location))):
            suites[category(test)].append(test)
    records = []
    for group, tests in suites.items():
        with (folder / (group + ".log")).open("w", encoding="utf-8") as stream:
            result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordingResult).run(unittest.TestSuite(tests))
        for row in result.records:
            row["level"] = group
        records.extend(result.records)
    junit(records, folder / "junit.xml")
    checks = []
    checks.append(command("js-syntax", ["node", "--check", "web-dashboard/app.js"], folder))
    checks.append(command("js-dom-regression", ["node", "tests/test_dashboard.js"], folder))
    checks.append(command("compose-config", ["docker", "compose", "-f", "freqtrade-bot/docker-compose.yml", "config", "--quiet"], folder))
    engine = command("docker-engine", ["docker", "info", "--format", "{{.ServerVersion}}"], folder, failure_status="BLOCKED")
    # Some Windows docker wrappers return 0 while printing a pipe connection error.
    if not re.fullmatch(r"\d+\.\d+\.\d+[^\r\n]*", (folder / engine["log"]).read_text(encoding="utf-8").strip()):
        engine["status"] = "BLOCKED"
        engine["reason"] = "No valid Docker ServerVersion; see connection error in log"
    checks.append(engine)
    dependency = command("browser-dependency", ["node", "-e", "require('./tests/system/node_modules/playwright-core')"], folder, failure_status="BLOCKED")
    checks.append(dependency)
    system_records = []
    if dependency["status"] == "PASS":
        env = {**os.environ, "TEST_ARTIFACT_DIR": str(folder / "system"), "TEST_PYTHON": sys.executable}
        checks.append(command("system-browser", ["node", "tests/system/dashboard.e2e.cjs"], folder, timeout=180, env=env))
        target = folder / "system/results.json"
        if target.is_file():
            system_records = json.loads(target.read_text(encoding="utf-8"))["results"]
    else:
        checks.append({"id": "system-browser", "status": "BLOCKED", "reason": "Run npm ci in tests/system"})
    xml_files = list((ROOT / "android-app/app/src/main").rglob("*.xml"))
    try:
        for file in xml_files:
            ET.parse(file)
        checks.append({"id": "android-xml", "status": "PASS", "files": len(xml_files)})
    except ET.ParseError as exc:
        checks.append({"id": "android-xml", "status": "FAIL", "detail": str(exc)})
    gradle = shutil.which("gradle")
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    checks.append({"id": "android-build", "status": "NOT_RUN" if gradle and sdk else "BLOCKED",
                   "gradle_available": bool(gradle), "sdk_configured": bool(sdk),
                   "reason": "Build/device test requires Android SDK and Gradle; XML parse is not a build"})
    checks.append({"id": "real-exchange-provider", "status": "NOT_RUN",
                   "reason": "No real orders, paid AI calls, live provider contracts or exchange execution in this offline run"})
    manifest = {}
    for base in ("freqtrade-bot", "web-dashboard", "android-app", "tests"):
        for path in (ROOT / base).rglob("*"):
            if any(p in ("node_modules", "__pycache__", ".gradle", "build", "data", "history", "logs") for p in path.parts):
                continue
            if path.is_file() and path.suffix in (".py", ".js", ".cjs", ".json", ".kt", ".xml", ".yml", ".kts") and path.name != "latest.json" and "secret" not in path.name:
                manifest[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    (folder / "source-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    summary = {group: {status: sum(r["level"] == group and r["status"] == status for r in records)
                       for status in ("PASS", "FAIL", "ERROR", "SKIP")} for group in suites}
    summary["system"] = {status: sum(r["status"] == status for r in system_records) for status in ("PASS", "FAIL")}
    document = {"started_at_utc": started.isoformat(), "started_at_vn": started.astimezone(timezone(timedelta(hours=7))).isoformat(),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(), "environment": {"python": sys.version, "platform": platform.platform()},
        "scope": "Offline software qualification. Freqtrade/TA-Lib/CCXT/paid AI replaced by fixtures where stated. Real Edge + mock API system tests.",
        "summary": summary, "python_tests": records, "system_tests": system_records, "checks": checks,
        "live_qualification": False, "source_manifest": "source-manifest.json"}
    (folder / "results.json").write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(folder), "summary": summary, "checks": [{"id": c["id"], "status": c["status"]} for c in checks]}, ensure_ascii=False, indent=2))
    return int(any(r["status"] in ("FAIL", "ERROR") for r in records + system_records + checks))


if __name__ == "__main__":
    raise SystemExit(main())
