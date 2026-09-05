#!/usr/bin/env python3
"""Reproducible micro-benchmark for AATable engine (_aawidth + aatable).

Run from repo root:
    python3 bench/bench_aatable.py

Deterministic: fixed seed, fixed datasets, repeated runs, reports
median + min + max in microseconds. No external dependencies.
"""
import os
import sys
import time
import random
import statistics
import json

# Ensure repo root is importable regardless of CWD
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from _aawidth import display_width, split_grapheme_clusters  # noqa: E402
from aatable import parse_md_table, parse_csv, render_aa_table  # noqa: E402


# ─────────────────────────────────────────────
# Datasets
# ─────────────────────────────────────────────

def _ascii_dataset(rows: int, cols: int) -> list:
    rng = random.Random(42)
    out = []
    for _ in range(rows):
        out.append([
            ''.join(rng.choices('abcdefghijklmnopqrstuvwxyz0123456789 ', k=rng.randint(3, 12)))
            for _ in range(cols)
        ])
    return out


def _cjk_dataset(rows: int, cols: int) -> list:
    rng = random.Random(43)
    kana = 'あいうえおかきくけこさしすせそたちつてとなにぬねの'
    han = '日本語入力評価表漢字情報処理'
    out = []
    for _ in range(rows):
        row = []
        for _ in range(cols):
            mix = rng.choice([kana, han, kana + han])
            n = rng.randint(2, 8)
            row.append(''.join(rng.choice(mix) for _ in range(n)))
        out.append(row)
    return out


def _mixed_dataset(rows: int, cols: int) -> list:
    rng = random.Random(44)
    out = []
    for r in range(rows):
        row = []
        for c in range(cols):
            if c % 2 == 0:
                row.append(''.join(rng.choices('abcdef', k=rng.randint(2, 6))))
            else:
                row.append(''.join(rng.choice('漢字日本') for _ in range(rng.randint(2, 6))))
        out.append(row)
    return out


def _emoji_dataset(rows: int, cols: int) -> list:
    rng = random.Random(45)
    emoji = ['😀', '🎉', '🇯🇵', '🇺🇸', '👨‍👩‍👧', '👋🏽', '🚀', '❤️', '🌸', '🍣']
    out = []
    for _ in range(rows):
        out.append([''.join(rng.choices(emoji, k=rng.randint(1, 3))) for _ in range(cols)])
    return out


DATASETS = {
    'ascii': _ascii_dataset,
    'cjk': _cjk_dataset,
    'mixed': _mixed_dataset,
    'emoji': _emoji_dataset,
}


def _bench(fn, iters: int = 200, warmup: int = 10) -> dict:
    for _ in range(warmup):
        fn()
    ts = []
    for _ in range(iters):
        t0 = time.perf_counter_ns()
        fn()
        ts.append(time.perf_counter_ns() - t0)
    us = [t / 1000.0 for t in ts]
    return {
        'iters': iters,
        'min_us': min(us),
        'median_us': statistics.median(us),
        'mean_us': statistics.mean(us),
        'max_us': max(us),
        'stdev_us': statistics.stdev(us) if len(us) > 1 else 0.0,
    }


def main():
    results = {}

    # --- Micro: display_width on single cells ---
    samples = {
        'ascii_cell': 'Hello',
        'cjk_cell': '漢字入力',
        'mixed_cell': 'Hello世界!',
        'emoji_cell': '👨‍👩‍👧🇯🇵😀',
    }
    for name, s in samples.items():
        results[f'dw_{name}'] = _bench(lambda s=s: display_width(s), iters=5000)

    # --- Micro: split_grapheme_clusters ---
    for name, s in samples.items():
        results[f'gc_{name}'] = _bench(lambda s=s: split_grapheme_clusters(s), iters=5000)

    # --- End-to-end: render_aa_table ---
    for ds_name, builder in DATASETS.items():
        for rows, cols in [(10, 4), (100, 6), (1000, 8)]:
            data = builder(rows, cols)
            key = f'render_{ds_name}_{rows}x{cols}'
            # Fewer iters for large
            iters = max(20, 300 - (rows * cols // 30))
            results[key] = _bench(lambda d=data: render_aa_table(d), iters=iters)

    # --- End-to-end: parse + render via stdin-ish strings ---
    md_input = '| a | b | c |\n|---|---|---|\n' + '\n'.join(
        f'| {r[0]} | {r[1]} | {r[2]} |' for r in _mixed_dataset(100, 3)
    )
    lines = md_input.split('\n')

    def _parse_and_render():
        rows = parse_md_table(lines)
        return render_aa_table(rows) if rows else ''

    results['pipe_md_100x3'] = _bench(_parse_and_render, iters=100)

    csv_text = '\n'.join(','.join(r) for r in _mixed_dataset(100, 5))

    def _csv_and_render():
        rows = parse_csv(csv_text.split('\n'), delimiter=',')
        return render_aa_table(rows) if rows else ''

    results['pipe_csv_100x5'] = _bench(_csv_and_render, iters=100)

    # --- Output ---
    print(json.dumps(results, indent=2, ensure_ascii=False))

    # Persist for comparison
    out_path = os.path.join(REPO_ROOT, 'bench', 'results_baseline.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f'\n[saved] {out_path}', file=sys.stderr)


if __name__ == '__main__':
    main()
