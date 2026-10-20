"""Demo (Agent 3): saved answers for the cached (no-GPU) fallback. No torch, no Gradio: testable anywhere.

build_cache()  runs example questions through the REAL pipeline once (on Colab) and returns the results
save_cache() / load_cache()  JSON file that the app can show later without any model
"""
import json
from pathlib import Path

from agent3_finetune.demo.pipeline import AUTO, MANUAL, run_all

# The questions are chosen to tell the story of the results. Edit freely: they are only inputs.
# Nothing here says which answers are right: the panel and you judge them together.
EXAMPLES = [
    {"title": "1. Easy: how many singers?", "db": "concert_singer",
     "question": "How many singers are there?"},
    {"title": "2. Single-join: albums by AC/DC", "db": "chinook",
     "question": "List the titles of all albums by the artist AC/DC."},
    # Examples 3-6 are two pairs for the routing demonstration. They were picked from the saved evaluation
    # results (find_wrong_head_examples.py) because the TRUE head answered correctly and another head did not.
    # They show the mechanism; they are NOT typical rates (see the benchmark table for those).
    {"title": "3. Top-5 country areas: the correct head (simple), set by hand", "db": "world_1",
     "question": "What are the names and areas of countries with the top 5 largest area?",
     "label_mode": MANUAL, "manual_label": "simple"},
    {"title": "4. Top-5 country areas: a wrong head (single-join), set by hand", "db": "world_1",
     "question": "What are the names and areas of countries with the top 5 largest area?",
     "label_mode": MANUAL, "manual_label": "single-join"},
    {"title": "5. Singers in 2014 concerts: the correct head (multi-join), set by hand", "db": "concert_singer",
     "question": "What are the names of the singers who performed in a concert in 2014?",
     "label_mode": MANUAL, "manual_label": "multi-join"},
    {"title": "6. Singers in 2014 concerts: a wrong head (simple), set by hand", "db": "concert_singer",
     "question": "What are the names of the singers who performed in a concert in 2014?",
     "label_mode": MANUAL, "manual_label": "simple"},
    {"title": "7. Aggregation: average life expectancy in Asia", "db": "world_1",
     "question": "What is the average life expectancy of the countries in Asia?"},
    {"title": "8. Aggregation with a join: cities per continent", "db": "world_1",
     "question": "How many cities are there in each continent?"},
    {"title": "9. Hard: car makers with 8-cylinder cars", "db": "car_1",
     "question": "What are the names of the car makers that produced a car with 8 cylinders?"},
    {"title": "10. Typos: the model gets a messy question", "db": "concert_singer",
     "question": "how mny singrs r there"},
    {"title": "11. Off-topic: nothing to do with the database", "db": "concert_singer",
     "question": "What is the weather in Colombo today?"},
]


def build_cache(engine, classifier, dbs, examples=EXAMPLES, meta=None):
    entries = []
    for ex in examples:
        res = run_all(engine, classifier, dbs, ex["question"], ex["db"],
                      ex.get("label_mode", AUTO), ex.get("manual_label", "simple"))
        entries.append({"title": ex["title"], "result": res})
    return {"meta": meta or {}, "examples": entries}


def save_cache(cache, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=1, default=str), encoding="utf-8")


def load_cache(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("examples"), list) or not data["examples"]:
        raise ValueError("this is not a demo cache file (no 'examples' list)")
    for e in data["examples"]:
        if "title" not in e or "result" not in e:
            raise ValueError("a cache entry is missing 'title' or 'result'")
    return data
