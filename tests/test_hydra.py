"""Tests for the HydraLoRA module. They need PyTorch, so they skip on a machine without it (run them in Colab):

    pip install -q pytest
    python -m pytest tests/test_hydra.py -v
"""
import pytest

pytest.importorskip("torch")

from agent3_finetune import hydra  # noqa: E402


def test_routing_gradients_parameters_and_lora_equivalence():
    """Runs the module's own checks: zero init, per-example routing, gradient isolation, n_heads=1 == LoRA, parameter counts."""
    hydra.run_tests()


def test_every_bucket_has_exactly_one_head():
    assert len(hydra.HEADS) == len(set(hydra.HEADS)) == 4
    assert [hydra.head_index(h) for h in hydra.HEADS] == [0, 1, 2, 3]


def test_head_order_matches_the_shared_complexity_buckets():
    complexity = pytest.importorskip("agent1_retrieval.complexity")
    assert tuple(complexity.BUCKETS) == hydra.HEADS


@pytest.mark.parametrize("label", [None, "", "garbage", "SIMPLE", 123, "multi join"])
def test_unknown_labels_never_crash_routing(label):
    """Non-functional requirement (reliability): routing handles any label by falling back to the default head."""
    assert hydra.head_index(label) == hydra.HEADS.index(hydra.DEFAULT_HEAD)


def test_trainable_parameter_numbers_for_the_report():
    assert hydra.expected_params(16, 1) == 18_464_768          # measured in the real LoRA run
    assert hydra.expected_params(16, 4) == 49_430_528          # HydraLoRA, 4 heads
    assert hydra.expected_params(43, 1) > hydra.expected_params(16, 4) * 0.99  # parameter-matched control
