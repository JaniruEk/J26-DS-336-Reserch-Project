"""Demo (Agent 3): Agent 1's live complexity classifier, loaded straight from its joblib file.

Why not `from agent1_retrieval.complexity import classify_query`?  Importing the package may pull in heavy
dependencies on Colab. `classify_query` is only `str(joblib.load(complexity_nl.joblib).predict([question])[0])`,
so this does the same thing directly. If the file cannot be loaded the demo falls back to Manual label mode.

Accuracy of this classifier on Agent 3's evaluation questions is only about 0.59 (see the handover): the app says so.
"""
from pathlib import Path

# agent3_finetune/demo/classifier.py -> project root is two folders up
DEFAULT_PATH = Path(__file__).resolve().parents[2] / "agent1_retrieval" / "complexity_nl.joblib"


class LiveClassifier:
    def __init__(self, path=None):
        self.path = Path(path) if path else DEFAULT_PATH
        self.error = None
        self._model = None
        try:
            import joblib
            self._model = joblib.load(self.path)
        except Exception as e:  # missing file, missing scikit-learn, version mismatch ...
            self.error = f"{type(e).__name__}: {e}"

    @property
    def available(self):
        return self._model is not None

    def predict(self, question):
        """Label for the question, or None if the classifier is not available or fails."""
        if self._model is None:
            return None
        try:
            return str(self._model.predict([question])[0])
        except Exception as e:
            self.error = f"{type(e).__name__}: {e}"
            return None
