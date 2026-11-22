"""Two zips to upload to Google Drive (MyDrive/j26_width/) for notebooks/width_sweep_colab.ipynb.

  python -m scripts.make_colab_bundle

data/colab/j26_code.zip = the committed code (git archive HEAD with LF line endings for bash; the commit id is the zip comment).
data/colab/j26_data.zip = every database the width sweep files name (Spider dev + train, Chinook, Northwind).
"""
import json
import subprocess
import zipfile
from pathlib import Path

OUT = Path("data/colab")
SETS = ["eval/spider_dev_full.json", "eval/chinook_pairs.json", "eval/northwind_pairs.json", "eval/spider_train_width.json"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if subprocess.run(["git", "status", "--porcelain", "--untracked-files=no", "agent1_retrieval", "scripts", "harness",
                       "src", "eval", "tests"], capture_output=True, text=True).stdout.strip():
        print("warning: uncommitted changes in code folders are NOT in the code zip")
    subprocess.run(["git", "-c", "core.autocrlf=false", "archive", "--format=zip", "-o", str(OUT / "j26_code.zip"), "HEAD"], check=True)
    dbs = sorted({p["db"] for f in SETS for p in json.loads(Path(f).read_text(encoding="utf-8"))})
    with zipfile.ZipFile(OUT / "j26_data.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for db in dbs:
            z.write(db, db)
    for f in ("j26_code.zip", "j26_data.zip"):
        print(f"{OUT / f}: {(OUT / f).stat().st_size / 1e6:.1f} MB")
    print(f"{len(dbs)} databases; commit {subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()}")


if __name__ == "__main__":
    main()
