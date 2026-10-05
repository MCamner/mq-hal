#!/usr/bin/env bash
# Consumer contract: mq-hal reads `mqlaunch doctor --json` (mq.doctor-status.v1).
#
# brief.py and doctor_summary.py parse that output. It had no schema, and
# doctor_summary's built-in sample used keys the real output never had
# (`message`), so the smoke tests ran against an invented shape. macos-scripts
# owns the contract; mq-hal keeps a byte-identical copy and proves here that
# its parsers handle the real shape.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDORED="$ROOT/schemas/vendor/mq.doctor-status.v1.json"
FIXTURE="$ROOT/tests/fixtures/doctor-status.v1.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export PYTHONPYCACHEPREFIX="$TMP/pycache"

echo "SMOKE: doctor status contract (mq.doctor-status.v1)"

echo "[1/5] vendored schema declares the contract"
python3 - "$VENDORED" <<'EOF'
import json, sys
schema = json.load(open(sys.argv[1]))
assert schema["properties"]["schema"]["const"] == "mq.doctor-status.v1", schema["properties"]["schema"]
print("  contract id: OK")
EOF

echo "[2/5] vendored copy matches macos-scripts"
# CI sets MQ_CANONICAL_MACOS_SCRIPTS_ROOT to a fresh checkout: there the owner's
# file must exist and match. Locally the sibling checkout is used when present;
# without one, drift is reported as unverified, not assumed absent.
canonical_root="${MQ_CANONICAL_MACOS_SCRIPTS_ROOT:-$HOME/macos-scripts}"
canonical="$canonical_root/schemas/mq.doctor-status.v1.json"
if [[ -f "$canonical" ]]; then
  cmp -s "$canonical" "$VENDORED" || {
    echo "FAIL: $VENDORED has drifted from $canonical — re-copy, do not edit" >&2
    exit 1
  }
  echo "  matches $canonical"
elif [[ -n "${MQ_CANONICAL_MACOS_SCRIPTS_ROOT:-}" ]]; then
  echo "FAIL: canonical schema missing: $canonical" >&2
  exit 1
else
  echo "  SKIP: no macos-scripts checkout; drift unverified"
fi

echo "[3/5] fixture and doctor_summary's sample conform to the schema"
python3 - "$ROOT" "$VENDORED" "$FIXTURE" <<'EOF'
import json, sys
root, schema_path, fixture_path = sys.argv[1:]
sys.path.insert(0, root + "/scripts")
import doctor_summary

schema = json.load(open(schema_path))
# Stdlib only, like the rest of this suite. A keyword this validator does not
# implement must fail the test, not pass unchecked.
SUPPORTED = {"$schema", "$id", "title", "description", "type", "const", "enum",
             "required", "properties", "additionalProperties", "items",
             "minimum", "minLength"}

def keywords(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            if key == "properties":
                for child in value.values():
                    yield from keywords(child)
            elif isinstance(value, dict):
                yield from keywords(value)

unknown = set(keywords(schema)) - SUPPORTED
assert not unknown, f"schema uses keywords this check cannot verify: {unknown}"

TYPES = {"object": dict, "array": list, "string": str, "null": type(None)}

def check(value, node, path="$"):
    errors = []
    types = node.get("type")
    if types:
        types = [types] if isinstance(types, str) else types
        ok = any((t == "integer" and isinstance(value, int) and not isinstance(value, bool))
                 or (t != "integer" and isinstance(value, TYPES[t])) for t in types)
        if not ok:
            return [f"{path}: expected {types}, got {type(value).__name__}"]
    if "const" in node and value != node["const"]:
        errors.append(f"{path}: expected {node['const']!r}, got {value!r}")
    if "enum" in node and value not in node["enum"]:
        errors.append(f"{path}: {value!r} not in {node['enum']}")
    if "minimum" in node and value < node["minimum"]:
        errors.append(f"{path}: {value} < {node['minimum']}")
    if "minLength" in node and len(value) < node["minLength"]:
        errors.append(f"{path}: shorter than {node['minLength']}")
    if isinstance(value, dict):
        for key in node.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing {key!r}")
        props = node.get("properties", {})
        for key, child in value.items():
            if key in props:
                errors.extend(check(child, props[key], f"{path}.{key}"))
            elif node.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected key {key!r}")
    if isinstance(value, list) and "items" in node:
        for i, item in enumerate(value):
            errors.extend(check(item, node["items"], f"{path}[{i}]"))
    return errors

for label, doc in (("fixture", json.load(open(fixture_path))),
                   ("doctor_summary.SAMPLE_DOCTOR_JSON", doctor_summary.SAMPLE_DOCTOR_JSON)):
    errors = check(doc, schema)
    assert not errors, f"{label} does not conform:\n  " + "\n  ".join(errors)
    print(f"  {label}: OK")

# The validator itself must reject a non-conforming document.
bad = json.load(open(fixture_path))
bad["checks"][0]["message"] = "git found"
assert check(bad, schema), "validator accepted an unknown key"
print("  validator rejects unknown keys: OK")
EOF

# A stub mqlaunch that prints the fixture, first on PATH, so the parsers read
# the contract shape through the same command they run for real.
mkdir -p "$TMP/bin"
cat >"$TMP/bin/mqlaunch" <<EOF
#!/usr/bin/env bash
[[ "\$*" == "doctor --json" ]] && cat "$FIXTURE"
EOF
chmod +x "$TMP/bin/mqlaunch"

echo "[4/5] brief.collect_doctor reads the contract"
PATH="$TMP/bin:$PATH" python3 - "$ROOT" "$TMP" <<'EOF'
import sys
from pathlib import Path
root, tmp = sys.argv[1:]
sys.path.insert(0, root + "/scripts")
import brief
result = brief.collect_doctor(Path(tmp))
assert result == {"health": "Warning", "ok": 3, "warn": 1, "fail": 0}, result
print("  brief:", result)
EOF

echo "[5/5] doctor_summary reads the contract"
# Called directly: the CLI resolves --repo through config/repos.json, and the
# parsing under test is run_doctor + deterministic_summary either way.
PATH="$TMP/bin:$PATH" python3 - "$ROOT" "$TMP" <<'EOF2'
import sys
from pathlib import Path
root, tmp = sys.argv[1:]
sys.path.insert(0, root + "/scripts")
import doctor_summary
data, _raw, command = doctor_summary.run_doctor(Path(tmp))
assert data["schema"] == "mq.doctor-status.v1", data
summary = doctor_summary.deterministic_summary(data)
# The counts come from the document's own summary. Walking every string
# counted the top-level "status": "warn" as a second warning and the check's
# "detail": "missing" as a serious issue — 1 serious, 2 warnings for a run
# with 0 failures and 1 warning.
assert summary["summary"] == "Detected 0 serious issue(s) and 1 warning(s) from doctor JSON.", summary
assert summary["status"] == "Mostly healthy, with warnings", summary
assert any("jq" in f for f in summary["key_findings"]), summary["key_findings"]
print("  doctor_summary:", summary["summary"])
EOF2

echo "OK: doctor status contract smoke test passed"
