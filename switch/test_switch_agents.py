"""Tests for KinCare's Switch layer: the agents' CLI and the Recall Watcher. No network, no Switch server.

Run: api\\.venv\\Scripts\\python -m pytest switch -q
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kincare_cli  # noqa: E402
import recall_watcher  # noqa: E402

FLAGGED = {
    "verdict": "alert_found",
    "matches": [{"score": 100, "alert": {
        "category": "nsq", "brand": "Namik-MR", "batch_no": "AT25-0938A",
        "reason": "The sample does not conform to declared formula, in respect of content of Aceclofenac.",
        "manufacturer": "Aspo Pharmaceuticals LLP.", "reported_by": "LUCKNOW, Uttar Pradesh",
        "alert_month": "2026-09", "mfg_date": "Nov-2025", "expiry": "Oct-2027",
        "alert_url": "https://cdscoonline.gov.in/CDSCO/viewPublicNSQDrug"}}],
}
CLEAN = {"verdict": "no_alert_found", "matches": []}


@pytest.fixture
def family(tmp_path, monkeypatch):
    monkeypatch.setattr(kincare_cli, "FAMILY", tmp_path / "family.json")
    monkeypatch.setattr(recall_watcher, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(kincare_cli, "get", lambda path, **p: FLAGGED if p.get("batch") == "AT25-0938A" else CLEAN)
    kincare_cli.main(["family-add", "Dadi", "Crocin", "CROCIN123X", "--times", "08:00,20:00"])
    kincare_cli.main(["family-add", "Dadi", "Namik-MR", "AT25-0938A", "--times", "09:00"])
    return tmp_path


def test_family_add_replaces_same_person_and_batch(family):
    kincare_cli.main(["family-add", "Dadi", "Namik-MR", "AT25-0938A", "--times", "21:00"])
    items = kincare_cli.load_family()
    assert len(items) == 2
    assert [m["times"] for m in items if m["batch"] == "AT25-0938A"] == [["21:00"]]


def test_family_check_flags_only_the_listed_batch(family):
    r = kincare_cli.family_check()
    assert r["checked"] == 2
    assert [f["batch"] for f in r["flagged"]] == ["AT25-0938A"]


def test_alert_text_is_factual_bilingual_and_hands_off():
    item = {"person": "Dadi", "brand": "Namik-MR", "batch": "AT25-0938A", "match": FLAGGED["matches"][0]}
    text = recall_watcher.alert_text(item)
    assert "AT25-0938A" in text and "Not of Standard Quality" in text and "LUCKNOW" in text
    assert "@kincare-pharmacist" in text                      # agent-to-agent handoff
    assert "हिंदी" in text                                     # Hindi for the elder
    assert "don't stop or switch" in text                     # human decides, never the agent
    assert ".." not in text


def test_watcher_alerts_once_per_batch(family, monkeypatch):
    posted = []
    monkeypatch.setattr(recall_watcher, "room_ids", lambda env: ["room-1"])
    monkeypatch.setattr(recall_watcher, "post", lambda env, room, text: posted.append((room, text)))
    assert recall_watcher.check_once({}) == 1
    assert recall_watcher.check_once({}) == 0                 # no repeat alert
    assert len(posted) == 1 and posted[0][0] == "room-1"


def test_dry_run_posts_nothing(family, monkeypatch, capsys):
    monkeypatch.setattr(recall_watcher, "post", lambda *a: pytest.fail("dry run must not post"))
    assert recall_watcher.check_once({}, dry=True) == 1
    assert "Recall alert for Dadi" in capsys.readouterr().out


def test_cli_reports_unreachable_api_as_json(monkeypatch, capsys):
    monkeypatch.setattr(kincare_cli, "API", "http://127.0.0.1:9")
    assert kincare_cli.main(["health"]) == 1
    assert "not reachable" in json.loads(capsys.readouterr().out)["error"]


def test_template_is_valid_yaml_with_all_agents():
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load((Path(__file__).parent / "kincare-room.template.yaml").read_text(encoding="utf-8"))
    names = {r["name"] for r in doc["resources"].values() if r["type"] == "agent"}
    assert names == {"kincare-scan", "kincare-pharmacist", "kincare-dose"}
    for name in names:
        assert (Path(__file__).parent / "agents" / name / "AGENT.md").is_file()
