"""Redraw the two system diagrams in pp1/ (black and white, matplotlib): python -m scripts.draw_flows

  pp1/PP1_Offline_Build_Flow.png  what Agents 2, 3 and 4 build once, before any question is answered
  pp1/PP1_Runtime_Flow.png        what happens for one question

Solid boxes run today; dashed, shaded boxes are stand-ins or planned. Edit the text here and re-run when the system
changes, so the pictures never drift from the code."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parents[1] / "pp1"
SHADE = "#e4e4e4"


def canvas(w, h):
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w), ax.set_ylim(h, 0), ax.axis("off")
    return fig, ax


def panel(ax, x, y, w, h, label):
    ax.add_patch(Rectangle((x, y), w, h, fc="#f6f6f6", ec="#8a8a8a", lw=1))
    ax.text(x + 12, y + 18, label, fontsize=11, weight="bold", va="center", color="#333")


def box(ax, x, y, w, h, title, lines=(), planned=False, size=10, title_size=11.5, align="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=7", lw=1.6, ec="black",
                                fc=SHADE if planned else "white", ls=(0, (5, 3)) if planned else "-"))
    tx, ha = (x + w / 2, "center") if align == "center" else (x + 16, "left")
    ax.text(tx, y + 20, title, fontsize=title_size, weight="bold", ha=ha, va="center")
    for i, line in enumerate(lines):
        ax.text(tx, y + 43 + 19 * i, line, fontsize=size, ha=ha, va="center")


def text(ax, x, y, s, size=10, **kw):
    ax.text(x, y, s, fontsize=size, va="center", **kw)


def arrow(ax, p1, p2, label=None, dashed=False, at=0.5, dx=6):
    ax.annotate("", xy=p2, xytext=p1, arrowprops=dict(arrowstyle="-|>", lw=1.6, color="black", mutation_scale=14,
                                                      shrinkA=0, shrinkB=0, ls=(0, (5, 3)) if dashed else "-"))
    if label:
        ax.text(p1[0] + (p2[0] - p1[0]) * at + dx, p1[1] + (p2[1] - p1[1]) * at, label, fontsize=9.5, va="center",
                bbox=dict(fc="white", ec="none", pad=1.5))


def down(ax, x, y1, y2, **kw):
    arrow(ax, (x, y1), (x, y2), **kw)


def offline():
    fig, ax = canvas(1800, 930)
    cols = [(30, "AGENT 2  -  Foundation model  (Wathsala)"), (630, "AGENT 3  -  Fine-tuning architecture  (Thathsarani)"),
            (1230, "AGENT 4  -  Mixed-precision quantization  (Karunanayake)")]
    for x, label in cols:
        panel(ax, x, 20, 540, 820, label)

    # Agent 2: distilled question classifier (the live question gate); the distilled SQL base is still planned
    a = 50
    box(ax, a, 60, 500, 85, "Teacher model: Qwen2.5-7B-Instruct",
        ["fine-tuned on the tasks first (an untuned teacher", "misled the student: accuracy 0.59)"])
    box(ax, a, 180, 500, 85, "Training data: two classification tasks",
        ["Task 1: database or general question (4,000)", "Task 2: prompt injection, safe or malicious (436)"])
    box(ax, a, 310, 240, 95, "KD student", ["Qwen2.5-1.5B-Instruct + LoRA", "learns the teacher's", "soft labels"])
    box(ax, a + 260, 310, 240, 95, "Native student", ["same model + LoRA,", "trained on the labels only", "(the control)"])
    box(ax, a, 440, 500, 95, "Compare KD vs native  (1,200 test questions)",
        ["Task 1: 0.994 vs 0.988 (not significant)", "Task 2: 0.948 vs 0.836 (p = 0.004)"])
    box(ax, a, 570, 500, 85, "Publish the KD student adapter",
        ["used live as the question gate (see the runtime flow)"])
    box(ax, a, 690, 500, 85, "Planned: distilled SQL base model",
        ["for Agent 3 to fine-tune; not built yet"], planned=True)
    down(ax, 300, 145, 180)
    down(ax, 170, 265, 310, label="trains")
    down(ax, 430, 265, 310)
    down(ax, 170, 405, 440)
    down(ax, 430, 405, 440)
    down(ax, 300, 535, 570)

    # Agent 3: LoRA vs HydraLoRA
    b = 650
    box(ax, b, 60, 500, 85, "Base model: Qwen2.5-1.5B-Instruct",
        ["the released model today;", "Agent 2's distilled base when it exists"])
    box(ax, b, 180, 500, 85, "Complexity-labelled training data",
        ["Spider train questions, each labelled simple / single-join /", "multi-join / aggregation by the shared classifier"])
    box(ax, b, 310, 240, 95, "Standard LoRA", ["one shared adapter,", "rank 16", "(control condition)"])
    box(ax, b + 260, 310, 240, 95, "HydraLoRA", ["shared A matrix,", "one B head per", "complexity bucket"])
    box(ax, b, 440, 500, 95, "Evaluation  (same base, data, epochs, hardware)",
        ["execution accuracy, 128 questions, one seed:", "LoRA 0.56  |  HydraLoRA 0.52 (true labels), 0.39 (live routing)"])
    box(ax, b, 570, 500, 85, "Publish winner AND runner-up",
        ["preliminary: winner LoRA, runner-up HydraLoRA", "(adapter files, config, evaluation log)"])
    down(ax, 900, 145, 180)
    down(ax, 770, 265, 310)
    down(ax, 1030, 265, 310)
    down(ax, 770, 405, 440)
    down(ax, 1030, 405, 440)
    down(ax, 900, 535, 570)
    arrow(ax, (550, 732), (650, 102), label="base model\n(planned)", dashed=True, at=0.62, dx=-40)

    # Agent 4: layer sensitivity -> INT4/INT8 allocation -> mixed model
    c = 1250
    box(ax, c, 60, 500, 85, "Layer sensitivity",
        ["each of the 28 layers set to INT4 on its own;", "how much SQL accuracy drops"])
    box(ax, c, 180, 500, 85, "Precision allocation",
        ["the most sensitive layers stay INT8 (6 of 28),", "the other 22 become INT4"])
    box(ax, c, 300, 500, 85, "Build the mixed INT4 / INT8 model",
        ["8-bit or 4-bit modules chosen per layer (bitsandbytes);", "memory close to uniform INT4"])
    box(ax, c, 420, 500, 105, "Compare: FP16, uniform INT8, uniform INT4, mixed",
        ["SQL accuracy, peak GPU memory, latency", "planned: llama.cpp Q4_K_M and random-layer", "controls; layers chosen on separate questions"])
    box(ax, c, 560, 500, 85, "Use in the app",
        ["today: J26_GENERATOR=adaptive_qwen (released Qwen)", "planned: one GGUF file run by llama.cpp"])
    box(ax, c, 680, 500, 105, "Planned: re-run on Agent 3's winner",
        ["the final allocation comes from the fine-tuned model;", "cross-check on the runner-up (proposed):", "do the same layers stay sensitive?"], planned=True)
    down(ax, 1500, 145, 180)
    down(ax, 1500, 265, 300)
    down(ax, 1500, 385, 420)
    down(ax, 1500, 525, 560)
    arrow(ax, (1150, 612), (1250, 732), label="winner +\nrunner-up\n(planned)", dashed=True, at=0.45, dx=-36)

    text(ax, 30, 870, "Offline: built once, before any question is answered.  Solid boxes run today; dashed, shaded boxes "
         "are planned.  Results are preliminary (released models, one seed).")
    text(ax, 30, 895, "Agent 4 replaced the earlier QAT vs PTQ comparison with adaptive mixed precision "
         "(scope change, 19 Oct 2026).")
    fig.savefig(OUT / "PP1_Offline_Build_Flow.png")
    plt.close(fig)


def runtime():
    fig, ax = canvas(2000, 1360)

    panel(ax, 20, 20, 1960, 190, "1  USER AND PRESENTATION")
    box(ax, 100, 70, 280, 100, "Analyst (user)", ["asks in plain English"])
    box(ax, 560, 55, 1100, 125, "Chat front end, Retrieval Explorer, dashboard",
        ["question box  |  database selector  |  generated SQL  |  result table and chart",
         "pipeline-trace panel (one section per agent)  |  save an answer as a dashboard chart"])
    arrow(ax, (380, 100), (560, 100), label="1  question", at=0.12, dx=0)
    arrow(ax, (560, 145), (380, 145), label="answer", at=0.75, dx=0)

    panel(ax, 20, 235, 1960, 260, "2  ORCHESTRATION  (FastAPI harness, shared)")
    box(ax, 60, 280, 520, 95, "Input validation",
        ["empty or too long question -> clear message", "databases chosen by name; adding one needs the admin token"])
    box(ax, 1340, 280, 600, 95, "Trace + structured log",
        ["every handoff: input, output, timing", "data/handoff.log.jsonl, shown in the trace panel"])
    box(ax, 60, 400, 1880, 75, "Pipeline controller",
        ["Agent 1 -> question gate (Agent 2) -> Agent 3 -> Agent 4   |   bounded retry (3 attempts, each logged)   |   "
         "stops with a clear message"])
    arrow(ax, (700, 180), (420, 280), label="2  POST /query", at=0.35, dx=10)
    down(ax, 320, 375, 400)
    arrow(ax, (1640, 400), (1640, 375))
    arrow(ax, (1640, 280), (1640, 180), label="8  response: SQL, rows, chart, trace", at=0.5, dx=10)

    panel(ax, 20, 520, 1960, 470, "3  LIVE AGENTS  (run once for every question)")
    top, h = 565, 400
    xs = [45, 530, 1015, 1500]
    w, sw = 455, 415

    def agent(x, title, subs, io):
        ax.add_patch(FancyBboxPatch((x, top), w, h, boxstyle="round,pad=0,rounding_size=7", lw=2, ec="black", fc="white"))
        ax.text(x + w / 2, top + 22, title, fontsize=11.5, weight="bold", ha="center", va="center")
        y = top + 45
        for t, line, planned in subs:
            box(ax, x + 20, y, sw, 62, t, [line], planned=planned, size=9.5, title_size=10.5)
            y += 72
        for i, s in enumerate(io):
            text(ax, x + 22, top + h - 50 + 22 * i, s, size=10)

    agent(xs[0], "AGENT 1  -  Retrieval and pruning  (Ekanayake)", [
        ("Complexity classifier (shared, schema-aware)", "simple / single-join / multi-join / aggregation", False),
        ("Anchor selection", "top-3 semantic matches (ChromaDB) or keyword match", False),
        ("FK-graph traversal", "adds the joined tables and the bridge tables between them", False),
        ("Column pruning", "keys kept; word, value and synonym matching; code values", False)],
        ["IN :  question + read-only database connection", "OUT:  pruned schema (JSON + DDL) + complexity label"])
    agent(xs[1], "AGENT 2  -  Question gate  (Wathsala)", [
        ("Distilled classifier", "Qwen2.5-1.5B KD student: database or general question?", False),
        ("Word check (Agent 1)", "a word of the question names a table or column", False),
        ("Decision", "passes only if both say database; otherwise declined", False),
        ("Planned: prompt-injection check", "her Task 2 model; waits for her exact prompt", True)],
        ["IN :  question (+ Agent 1's word check)", "OUT:  pass, or a clear decline message"])
    agent(xs[2], "AGENT 3  -  SQL generation  (Thathsarani)", [
        ("Head selection (planned)", "the LoRA adapter, or the HydraLoRA head for the label", True),
        ("SQL generation", "writes the SQL; uses the error hint on a retry", False),
        ("Today: stand-in model", "phi3 via Ollama, or Agent 4's adaptive Qwen", True),
        ("Chosen by J26_GENERATOR", "ollama:<model>  or  adaptive_qwen (NVIDIA GPU)", False)],
        ["IN :  question + pruned schema + label (+ hint)", "OUT:  candidate SQL"])
    agent(xs[3], "AGENT 4  -  Quantized execution  (Karunanayake)", [
        ("SQL safety guard", "SELECT only, one statement, read-only, time limit", False),
        ("Execution (stand-in runner)", "runs the SQL on the read-only database", True),
        ("Error diagnosis (stand-in)", "today the raw database error is the hint", True),
        ("Planned: empty-result check", "0 rows after a filter -> real values as a hint", True)],
        ["IN :  candidate SQL", "OUT:  rows, or error + hint"])

    # controller <-> agents (labels sit in the gap between the panels)
    pairs = [("3  question + DB", "pruned schema + label"), ("4  question", "pass / decline"),
             ("5  schema + label", "candidate SQL"), ("6  SQL", "rows, or error + hint")]
    for x, (go, back) in zip(xs, pairs):
        arrow(ax, (x + 110, 475), (x + 110, top), label=go, at=0.5, dx=6)
        arrow(ax, (x + 330, top), (x + 330, 475), label=back, at=0.5, dx=6)
    arrow(ax, (xs[2] + 420, 475), (xs[2] + 420, top), dashed=True)
    ax.text(xs[2] + 428, 545, "7  retry\n    with hint", fontsize=9, va="center", bbox=dict(fc="white", ec="none", pad=1))

    panel(ax, 20, 1015, 1960, 300, "4  DATA AND MODEL STORES")
    box(ax, 60, 1060, 330, 85, "ChromaDB schema index", ["table-DDL embeddings"])
    box(ax, 530, 1055, 1110, 100, "Model store",
        ["Qwen2.5-1.5B-Instruct  |  Agent 2's gate adapter  |  Agent 4's INT4/INT8 layer plan (results/qwen)",
         "Agent 3's LoRA / HydraLoRA adapters (planned)  |  Ollama stand-in models"])
    box(ax, 60, 1195, 1880, 85, "Target databases  (read-only login)",
        ["Chinook  |  TPC-H  |  Spider  |  Northwind  |  uploaded SQLite files  |  PostgreSQL servers"])
    down(ax, 150, top + h, 1060, label="semantic anchor search", at=0.5)
    down(ax, 450, top + h, 1195, label="reflect schema, sample code values", at=0.86)
    down(ax, xs[1] + 225, top + h, 1055, label="loads gate adapter", at=0.5)
    down(ax, xs[2] + 225, top + h, 1055, label="loads the model", at=0.5)
    down(ax, xs[3] + 225, top + h, 1195, label="execute SELECT", at=0.5)

    text(ax, 20, 1340, "Solid boxes run today.  Dashed, shaded boxes are stand-ins or planned.  Dashed arrow = failure "
         "path.  The numbers give the order of one question.  Updated 21 Oct 2026.")
    fig.savefig(OUT / "PP1_Runtime_Flow.png")
    plt.close(fig)


if __name__ == "__main__":
    offline()
    runtime()
    print("wrote", OUT / "PP1_Offline_Build_Flow.png", "and", OUT / "PP1_Runtime_Flow.png")
