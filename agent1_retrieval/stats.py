"""Paired comparison helpers: exact McNemar test for per-query correctness, bootstrap CI for per-query differences."""
import random
from math import comb
from statistics import mean


def mcnemar_exact(only_a, only_b):
    """Two-sided exact p for discordant pairs (queries only A got right vs only B got right)."""
    n, k = only_a + only_b, min(only_a, only_b)
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def bootstrap_ci(diffs, n=2000, seed=0):
    rnd = random.Random(seed)
    means = sorted(mean(rnd.choices(diffs, k=len(diffs))) for _ in range(n))
    return mean(diffs), means[int(0.025 * n)], means[int(0.975 * n) - 1]
