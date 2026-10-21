"""Demo (Agent 3): panel demo app. Same question, three models side by side.

Start on Colab (GPU), from the project root, after mounting Drive:
  !pip install -q gradio
  !python -m agent3_finetune.demo.app \
      --lora /content/drive/MyDrive/agent3/runs/lora_r16_seed42/adapter \
      --hydra /content/drive/MyDrive/agent3/runs/hydra_r16_seed42/adapter \
      --db-dir /content/drive/MyDrive/agent3/demo_dbs --share
It prints a public link ("Running on public URL: https://....gradio.live"): open that link in the browser.

Saved-answers mode (no GPU, runs on the laptop; add --db-dir to also browse the databases):
  python -m agent3_finetune.demo.app --cached agent3_finetune/demo/cache/examples.json [--db-dir <folder>]

Status: the live screen opened on Colab and answered a question. The database viewer, the auto-loaded first
cached example and the cached screen are written but not yet seen in a browser by the author.
"""
import argparse

from agent3_finetune.demo.dbinfo import describe_markdown
from agent3_finetune.demo.pipeline import AUTO, LABELS, MANUAL, MODES, list_databases, run_all

TITLES = {"base": "Before fine-tuning (base model)", "lora": "After fine-tuning (LoRA)",
          "hydra": "After fine-tuning (HydraLoRA)"}

BENCHMARK = """### My benchmark numbers
Execution accuracy on 128 questions (Spider dev + Chinook). One seed, placeholder base model
(Qwen2.5-1.5B-Instruct), about 31 questions per bucket.

| Type | Base | LoRA | Hydra |
|---|---|---|---|
| simple | 0.55 | 0.77 | 0.71 |
| single-join | 0.29 | **0.74** | 0.65 |
| multi-join | 0.25 | 0.16 | 0.16 |
| aggregation | 0.56 | 0.59 | 0.56 |
| **overall** | **0.41** | **0.56** | **0.52** |

Hydra = HydraLoRA given the **true** complexity label. With the **live classifier** (what you get in Auto
mode) it scores **0.39**: the classifier is right only about 59% of the time.

**What this shows**
- Fine-tuning clearly helps single-join questions (0.29 to 0.74).
- No detectable gain on multi-join or aggregation: multi-join is still hard.
- HydraLoRA did **not** beat plain LoRA. Each head is best on its own question type, but a wrong head costs a lot:
  switch the label to a wrong one and watch the HydraLoRA answer change.

There is no automatic right/wrong mark here: a new question has no gold answer, so we judge the results together.
"""


def build_ui(engine, classifier, dbs, cached=None):
    import gradio as gr
    import pandas as pd

    def placeholder(text):  # an empty table with a readable header instead of Gradio's "1 2 3"
        return pd.DataFrame({text: []})

    def to_frame(m):
        if not m["columns"]:
            return placeholder("(no result: the query did not run)")
        return pd.DataFrame(m["rows"], columns=m["columns"])

    def respond(question, db_name, label_mode, manual_label):
        return render(run_all(engine, classifier, dbs, question, db_name, label_mode, manual_label))

    def render(res):
        """Turn one result dict (live or saved) into the values for the screen."""
        if "error" in res:
            blank = []
            for _ in MODES:
                blank += ["", placeholder("(no answer)"), ""]
            return [f"**{res['error']}**", ""] + blank
        out = [f"**You asked** ({res['db']}): {res['question']}",
               f"{res['label_note']}  \nHydraLoRA routed to the **{res['routed_head']}** head."]
        for m in MODES:
            r = res["modes"][m]
            secs = f" ({r['seconds']} s to write the SQL)" if r["seconds"] is not None else ""
            head = f" Head used: **{r['head']}**." if r["head"] else ""
            out += [f"**{r['status']}**{secs}{head}", to_frame(r), r["sql"]]
        return out

    def add_browser(db_dropdown, first):
        """Accordion that shows the tables, columns, links and a few rows of the chosen database."""
        with gr.Accordion("Show the database: tables, columns and a few rows", open=False):
            md = gr.Markdown(describe_markdown(dbs[first], first))
        db_dropdown.change(lambda n: describe_markdown(dbs[n], n), [db_dropdown], [md])

    with gr.Blocks(title="Agent 3 demo: LoRA vs HydraLoRA") as demo:
        if cached is None:
            gr.Markdown("## Agent 3 demo: the same question, three models\n"
                        "Type any question about the chosen database. The SQL is run **read-only**, one SELECT only, "
                        "5-second limit, at most 20 rows.")
        else:
            meta = cached.get("meta", {})
            gr.Markdown("## Agent 3 demo: the same question, three models (SAVED ANSWERS)\n"
                        f"**These are saved answers, not a live run.** Recorded {meta.get('recorded_at', '?')} on "
                        f"{meta.get('gpu', '?')} from the live system. Pick an example below.")
        with gr.Row():
            with gr.Column(scale=3):
                q_md = gr.Markdown("")
                label_md = gr.Markdown("")
                outs = []
                with gr.Row():
                    for m in MODES:
                        with gr.Column():
                            gr.Markdown(f"### {TITLES[m]}")
                            status = gr.Markdown("")
                            table = gr.Dataframe(value=placeholder("(no answer yet)"), interactive=False)
                            with gr.Accordion("Show SQL", open=False):
                                sql = gr.Textbox(show_label=False, interactive=False, lines=4)
                            outs += [status, table, sql]
            with gr.Column(scale=2):
                gr.Markdown(BENCHMARK)
        outputs = [q_md, label_md] + outs
        if cached is None:
            question = gr.Textbox(label="Your question", placeholder="For example: How many singers are there?")
            with gr.Row():
                db = gr.Dropdown(choices=list(dbs), value=next(iter(dbs), None), label="Database")
                mode = gr.Radio([AUTO, MANUAL],
                                value=AUTO if classifier is not None and classifier.available else MANUAL,
                                label="Complexity label")
                manual = gr.Dropdown(list(LABELS), value="simple", label="Manual label (used only in Manual mode)")
            if dbs:
                add_browser(db, next(iter(dbs)))
            go = gr.Button("Ask", variant="primary")
            inputs = [question, db, mode, manual]
            go.click(respond, inputs, outputs)
            question.submit(respond, inputs, outputs)
        else:
            titles = [e["title"] for e in cached["examples"]]
            by_title = {e["title"]: e["result"] for e in cached["examples"]}
            pick = gr.Dropdown(titles, value=titles[0], label="Saved example")
            go = gr.Button("Show saved answer", variant="primary")
            go.click(lambda t: render(by_title[t]), [pick], outputs)
            pick.change(lambda t: render(by_title[t]), [pick], outputs)
            demo.load(lambda: render(by_title[titles[0]]), None, outputs)  # show the first example at start-up
            if dbs:  # databases given with --db-dir: let the panel look inside them (questions stay saved ones)
                first = next(iter(dbs))
                add_browser(gr.Dropdown(list(dbs), value=first, label="Browse a database"), first)
    return demo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lora", default="")
    ap.add_argument("--hydra", default="")
    ap.add_argument("--db-dir", default="", help="folder with the SQLite files to offer (searched recursively)")
    ap.add_argument("--classifier", default="", help="path to complexity_nl.joblib (default: agent1_retrieval folder)")
    ap.add_argument("--cached", default="", help="show SAVED answers from this examples.json: no GPU, no model")
    ap.add_argument("--share", action="store_true", help="make a public Gradio link (needed on Colab)")
    a = ap.parse_args()

    if a.cached:  # last-resort mode: runs on the laptop with only gradio installed
        from agent3_finetune.demo.cache import load_cache
        dbs = list_databases(a.db_dir) if a.db_dir else {}
        build_ui(None, None, dbs, cached=load_cache(a.cached)).queue().launch(share=a.share)
        return
    if not (a.lora and a.hydra and a.db_dir):
        raise SystemExit("live mode needs --lora, --hydra and --db-dir (or use --cached <examples.json>)")

    from agent3_finetune.demo.classifier import LiveClassifier
    from agent3_finetune.demo.engine import Engine

    dbs = list_databases(a.db_dir)
    if not dbs:
        raise SystemExit(f"no SQLite files found under {a.db_dir}")
    print("databases:", ", ".join(dbs))
    classifier = LiveClassifier(a.classifier or None)
    print("live classifier:", "ready" if classifier.available else f"NOT available ({classifier.error}) -> Manual mode")
    engine = Engine(a.lora, a.hydra)
    print("model ready on", engine.gpu)
    build_ui(engine, classifier, dbs).queue().launch(share=a.share)


if __name__ == "__main__":
    main()
