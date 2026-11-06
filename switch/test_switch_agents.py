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


def test_watcher_answers_check_once_then_says_still_flagged(family):
    first = recall_watcher.reply_to("@kincare-recall-watcher check now", {}, "room-1")
    assert "Recall alert for Dadi" in first and "@kincare-pharmacist" in first
    second = recall_watcher.reply_to("जाँच करो", {}, "room-1")
    assert "Still flagged (already raised)" in second and "Recall alert" not in second


def test_watcher_status_and_help(family):
    assert "I watch 2 medicines" in recall_watcher.reply_to("status", {"KINCARE_WATCH_MINUTES": "5"}, "r")
    assert "every 5 min" in recall_watcher.reply_to("status", {"KINCARE_WATCH_MINUTES": "5"}, "r")
    assert "CDSCO" in recall_watcher.reply_to("hello?", {}, "r")


def test_salts_of_reads_an_alert_product_name():
    assert kincare_cli.salts_of("Aceclofenac, Paracetamol & Chlorzoxazone Tablets") == ["aceclofenac", "paracetamol", "chlorzoxazone"]
    assert kincare_cli.salts_of("Telmisartan 40 mg and Hydrochlorothiazide 12.5 mg Tablets IP") == ["telmisartan", "hydrochlorothiazide"]
    assert kincare_cli.form_of("Aceclofenac, Paracetamol & Chlorzoxazone Tablets") == "tablet"


def _med(id, name, salts, maker, alerts, unit, form="tablet"):
    return {"id": id, "name": name, "salts": salts, "maker": maker, "form": form, "unit_price": unit,
            "price": unit * 10, "pack": "strip of 10", "maker_record": {"alerts": alerts}}


def test_replacements_keep_only_same_salts_clean_makers(monkeypatch):
    pool = [
        # the dataset dropped chlorzoxazone from salts, but the name has all three: keep
        _med(1, "StayHappi Aceclofenac+Chlorzoxazone+Paracetamol Tablet", "aceclofenac (100mg) + paracetamol (325mg)", "Sarvagunaushdhi", 0, 2.7),
        # a different medicine (serratiopeptidase, no chlorzoxazone): drop
        _med(2, "Rumatab SP Tablet", "aceclofenac (100mg) + paracetamol (325mg) + serratiopeptidase (15mg)", "Simpson", 0, 0.5),
        # right salts, maker with alerts: drop
        _med(3, "Aclo MR Aceclofenac Paracetamol Chlorzoxazone", "aceclofenac + paracetamol + chlorzoxazone", "Risky Labs", 4, 1.0),
        # right salts, wrong form: drop
        _med(4, "Gel Aceclofenac Paracetamol Chlorzoxazone", "aceclofenac + paracetamol + chlorzoxazone", "Clean Co", 0, 0.1, form="gel"),
        _med(5, "Genericart Aceclofenac+Paracetamol+Chlorzoxazone Tablet", "aceclofenac (100mg) + paracetamol (325mg)", "Swast", 0, 8.2),
    ]

    def fake_get(path, **p):
        if path == "/api/check":
            return FLAGGED | {"matches": [{"alert": FLAGGED["matches"][0]["alert"] | {"product_name": "Aceclofenac, Paracetamol & Chlorzoxazone Tablets"}}]}
        if path == "/api/medicines/search":
            return pool
        return {"alternatives": []}

    monkeypatch.setattr(kincare_cli, "get", fake_get)
    r = kincare_cli.replacements("AT25-0938A")
    assert [o["id"] for o in r["options"]] == [1, 5]          # cheapest first, unsafe ones gone


def test_replacements_for_a_clean_batch_offer_nothing(monkeypatch):
    monkeypatch.setattr(kincare_cli, "get", lambda path, **p: CLEAN)
    r = kincare_cli.replacements("AML24017")
    assert r["flagged"] is False and r["options"] == []


def test_template_is_valid_yaml_with_all_agents():
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load((Path(__file__).parent / "kincare-room.template.yaml").read_text(encoding="utf-8"))
    names = {r["name"] for r in doc["resources"].values() if r["type"] == "agent"}
    assert names == {"kincare-scan", "kincare-pharmacist", "kincare-dose"}
    for name in names:
        assert (Path(__file__).parent / "agents" / name / "AGENT.md").is_file()
