"""Demo (Agent 3): the logic behind one question, with no screen code (so it can be tested without Gradio/torch).

question + database + label choice  ->  label  ->  SQL from base / LoRA / HydraLoRA  ->  safe execution
"""
from pathlib import Path

from agent3_finetune.demo.sql_runner import run_query

LABELS = ("simple", "single-join", "multi-join", "aggregation")  # same as hydra.HEADS
AUTO = "Auto (live classifier)"
MANUAL = "Manual"
MODES = ("base", "lora", "hydra")
DB_SUFFIXES = (".sqlite", ".sqlite3", ".db")


def list_databases(db_dir):
    """{name: path} for every SQLite file under db_dir (name = file name without suffix)."""
    out = {}
    root = Path(db_dir)
    if root.exists():
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.suffix.lower() in DB_SUFFIXES:
                out.setdefault(p.stem, str(p))
    return out


def resolve_label(question, label_mode, manual_label, classifier):
    """Returns (label or None, plain-English note). None means: HydraLoRA will use its fallback head."""
    if label_mode == MANUAL:
        return manual_label, f"Manual label: **{manual_label}**"
    label = classifier.predict(question) if classifier is not None else None
    if label is None:
        return None, "Live classifier not available: HydraLoRA used its fallback head (single-join)."
    if label not in LABELS:
        return None, f"Live classifier returned an unknown label ('{label}'): fallback head (single-join) used."
    return label, f"Live classifier says: **{label}** (it is right only about 59% of the time)"


def run_all(engine, classifier, dbs, question, db_name, label_mode, manual_label):
    """One question through all three models. Never raises. Returns a dict for the screen."""
    question = (question or "").strip()
    if not question:
        return {"error": "Please type a question first."}
    if db_name not in dbs:
        return {"error": "Please choose a database."}
    label, note = resolve_label(question, label_mode, manual_label, classifier)
    answers = engine.answer(question, dbs[db_name], label)
    modes = {}
    for m in MODES:
        a = answers.get(m, {"error": "no answer"})
        if "error" in a:
            modes[m] = {"sql": "", "status": "Failed: " + a["error"], "columns": [], "rows": [],
                        "seconds": None, "head": None, "ok": False}
            continue
        r = run_query(dbs[db_name], a["sql"])
        modes[m] = {"sql": a["sql"], "status": r["status"], "columns": r["columns"], "rows": r["rows"],
                    "seconds": a["seconds"], "head": a.get("head"), "ok": r["ok"]}
    return {"question": question, "db": db_name, "label": label, "label_note": note,
            "routed_head": engine.head_for(label), "modes": modes}
