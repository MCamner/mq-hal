#!/usr/bin/env bash
# Consumer contract: mq-hal reads `mq-agent stack {cockpit,release-check,
# provenance} --json`.
#
# mq-agent owns those schemas; mq-hal keeps byte-identical copies in
# schemas/vendor/ (runtime_identity too, which provenance $refs). The parsers
# here were written against invented shapes — hal/stack.py and hal/release.py
# both carry samples the real output never had — and the release view showed
# readiness `unknown` for every repo on real data, because real items carry
# `blockers` rather than `ready`/`status`.
#
# Needs jsonschema (provenance uses oneOf/if/$ref, beyond a stdlib check). CI
# installs it; a missing module fails here rather than skipping.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export PYTHONPYCACHEPREFIX="$TMP/pycache"

echo "SMOKE: mq-agent stack contracts"

echo "[1/4] vendored copies match mq-agent"
# CI sets MQ_CANONICAL_AGENT_ROOT to a checkout of the owner's schemas: there
# they must exist and match. Locally the sibling checkout is used when present.
canonical_root="${MQ_CANONICAL_AGENT_ROOT:-$HOME/mq-agent}"
for name in mq_stack_cockpit mq_stack_release_check stack_provenance runtime_identity; do
  vendored="$ROOT/schemas/vendor/$name.schema.json"
  canonical="$canonical_root/schemas/$name.schema.json"
  if [[ -f "$canonical" ]]; then
    cmp -s "$canonical" "$vendored" || {
      echo "FAIL: $vendored has drifted from $canonical — re-copy, do not edit" >&2
      exit 1
    }
    echo "  $name: matches"
  elif [[ -n "${MQ_CANONICAL_AGENT_ROOT:-}" ]]; then
    echo "FAIL: canonical schema missing: $canonical" >&2
    exit 1
  else
    echo "  $name: SKIP, no mq-agent checkout; drift unverified"
  fi
done

echo "[2/4] fixtures conform to the schemas"
python3 - "$ROOT" <<'EOF'
import json, sys
from pathlib import Path
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

root = Path(sys.argv[1])
vendor = root / "schemas" / "vendor"
load = lambda n: json.loads((vendor / f"{n}.schema.json").read_text(encoding="utf-8"))
identity = load("runtime_identity")
registry = Registry().with_resource(identity["$id"], Resource.from_contents(identity))
for fixture, schema in (("stack-cockpit", "mq_stack_cockpit"),
                        ("stack-release-check", "mq_stack_release_check"),
                        ("stack-provenance", "stack_provenance")):
    doc = json.loads((root / "tests" / "fixtures" / f"{fixture}.json").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(load(schema), registry=registry).iter_errors(doc))
    assert not errors, f"{fixture}: " + "; ".join(e.message for e in errors[:5])
    print(f"  {fixture}: OK")
EOF

# A stub mq-agent, found through MQ_AGENT_BIN as the real one is, that prints
# the fixture for the subcommand it is asked for.
cat >"$TMP/mq-agent" <<EOF
#!/usr/bin/env bash
case "\$2" in
  cockpit) cat "$ROOT/tests/fixtures/stack-cockpit.json" ;;
  release-check) cat "$ROOT/tests/fixtures/stack-release-check.json" ;;
  provenance) cat "$ROOT/tests/fixtures/stack-provenance.json" ;;
  *) exit 2 ;;
esac
EOF
chmod +x "$TMP/mq-agent"
export MQ_AGENT_BIN="$TMP/mq-agent"

echo "[3/4] stack and provenance read the contract"
python3 - "$ROOT" <<'EOF'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
from hal import provenance, stack

fixture = json.loads((root / "tests/fixtures/stack-cockpit.json").read_text())
result = stack.read_cockpit()
assert result.ok, result.error
assert stack._overall(result.data) == fixture["overall_gate"], stack._overall(result.data)
names = [stack._name(item) for item in stack._items(result.data)]
assert names == [repo["repo"] for repo in fixture["repos"]], names
assert all(stack._status(item) != "UNKNOWN" for item in stack._items(result.data))
print("  cockpit:", stack._overall(result.data), names)

prov = provenance.read_provenance()
assert prov.data is not None, prov.error
print("  provenance: accepted", prov.data["schema"])
EOF

echo "[4/4] release reads readiness from the contract"
python3 - "$ROOT" <<'EOF'
import sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
from hal import release

data, _raw, code = release.read_release_check()
assert data is not None and code == 0, (code, _raw[:200])
rows = [(release.repo_name(i), release.ready(i), len(release.blockers(i))) for i in release.repos(data)]
# Fixture: first repo blocked, second only warned, third clean. Warnings do not
# block a release; a blocker does.
assert [r[1] for r in rows] == ["no", "yes", "yes"], rows
assert rows[0][2] == 1 and rows[1][2] == 0, rows
assert release.all_blockers(data) == [{"repo": rows[0][0], "blocker": data["repos"][0]["blockers"][0]}]
print("  release:", rows)
EOF

echo "OK: mq-agent stack contracts smoke test passed"
