"""Copy a sweep file through a narrow channel (cluster job output) as its difference from a file both sides have.

  python -m scripts.width_delta make  <base.jsonl> <new.jsonl>            -> prints the delta (xz + base64)
  python -m scripts.width_delta apply <base.jsonl> <delta.txt> <out.jsonl>  -> rebuilds new.jsonl, checks sha256

The base is the laptop's committed file for the same questions; rows that share an id with the base are sent as
only the fields (or per-width values) that differ, other rows whole. The rebuilt file must match the sha256 of the
original byte for byte, or apply fails.
"""
import base64
import gzip
import hashlib
import lzma
import json
import sys
from pathlib import Path


def _rows(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines()]


def make(base, new):
    b = {r["id"]: r for r in _rows(base)}
    text = Path(new).read_text(encoding="utf-8")
    out = []
    for r in map(json.loads, text.splitlines()):
        old = b.get(r["id"])
        if old is None or list(old) != list(r):
            out.append({"row": r})
            continue
        d = {}
        for k, v in r.items():
            if isinstance(v, dict) and isinstance(old[k], dict) and list(v) == list(old[k]):
                sub = {w: x for w, x in v.items() if old[k][w] != x}
                if sub:
                    d[k] = sub
            elif v != old[k]:
                d[k] = {"=": v}
        out.append({"id": r["id"], "d": d} if d else {"id": r["id"]})
    payload = {"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "rows": out}
    changed = lambda k: sum(len(e.get("d", {}).get(k, {})) for e in out)
    same_order = [e.get("id") for e in out] == list(b)
    print(f"{new}: {len(out)} rows ({sum('row' in e for e in out)} not in the base), same order as the base: "
          f"{same_order}; changed values: sql {changed('sql')}, ok {changed('ok')}, runs {changed('runs')}, "
          f"tokens {changed('tokens')}, features {changed('features')}", file=sys.stderr)
    return base64.b64encode(lzma.compress(json.dumps(payload).encode(), preset=9 | lzma.PRESET_EXTREME)).decode()


def apply(base, delta, out):
    b = {r["id"]: r for r in _rows(base)}
    raw = base64.b64decode("".join(Path(delta).read_text().split()))
    payload = json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else lzma.decompress(raw))  # old gzip or xz
    lines = []
    for e in payload["rows"]:
        if "row" in e:
            r = e["row"]
        else:
            r = b[e["id"]]
            for k, sub in e.get("d", {}).items():
                if "=" in sub:
                    r[k] = sub["="]
                else:
                    r[k].update(sub)
        lines.append(json.dumps(r) + "\n")
    text = "".join(lines)
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != payload["sha256"]:
        raise SystemExit("sha256 mismatch: the rebuilt file differs from the original; nothing written")
    Path(out).write_bytes(text.encode("utf-8"))  # bytes: no CRLF translation on Windows (the sha256 is of LF text)
    print(f"{out}: {len(lines)} rows, sha256 ok")


if __name__ == "__main__":
    if sys.argv[1] == "make":
        print(make(sys.argv[2], sys.argv[3]))
    else:
        apply(*sys.argv[2:5])
