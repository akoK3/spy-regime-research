"""Record the NumPy 2 string endpoint compatibility amendment; preserve v1."""
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from section4_3_1_candidates import sha256

root = Path(__file__).resolve().parent
old = root/"protocol_20261029T032504Z.json"
assert sha256(old) == old.with_suffix(".sha256").read_text().split()[0]
p = json.loads(old.read_text(encoding="utf-8"))
for item in p["implementation_files"]:
    assert sha256(root/"implementation_v1"/item["name"]) == item["sha256"]
now = datetime.now(timezone.utc)
stamp = now.strftime("%Y%m%dT%H%M%SZ")
p["protocol_id"] = f"section4_3_0_v2_{stamp}"
p["frozen_utc"] = now.isoformat()
p["frozen_america_new_york"] = now.astimezone(ZoneInfo("America/New_York")).isoformat()
p["supersedes_frozen_protocol"] = dict(file=old.name, sha256=sha256(old))
p["amendment_log"] = [dict(reason="First full-data run failed at a date-endpoint assertion: NumPy 2.5 does not reduce Unicode arrays with min/max. No feature file or score was produced.",
    code_change="Check first/last session labels on already time-sorted data; add loader/availability regression test.",
    scientific_decisions_changed=False, partial_run_directory="results", previous_implementation="implementation_v1")]
p["implementation_files"] = [dict(name=name, sha256=sha256(root/name)) for name in
    ["section4_3_1_candidates.py","test_candidates.py","audit_and_freeze.py","amend_protocol.py"]]
new = root/f"protocol_{stamp}.json"
assert not new.exists()
new.write_text(json.dumps(p,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
digest = sha256(new)
new.with_suffix(".sha256").write_text(f"{digest}  {new.name}\n", encoding="ascii")
(root/"FROZEN_PROTOCOL.txt").write_text(f"{new.name}\nSHA-256: {digest}\nFrozen UTC: {now.isoformat()}\nFrozen New York: {p['frozen_america_new_york']}\nSupersedes: {old.name}\n",encoding="utf-8")
print(new.name)
print(digest)
