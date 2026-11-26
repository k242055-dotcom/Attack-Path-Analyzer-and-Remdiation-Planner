"""Check the paired timing, metric aggregation and experiment artifacts."""

import csv
import json
from collections import defaultdict
from statistics import mean, median, pstdev

import pytest
from matplotlib.axes import Axes

from src.experiments import SUMMARY_FIELDS, TIMING_FIELDS, run_experiments, verify_checked_cases


def _read_table(path, expected_header):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert tuple(reader.fieldnames) == expected_header
        return list(reader)


def test_run_exports_paired_valid_results_and_measured_charts(tmp_path, monkeypatch):
    plotted = defaultdict(list)
    original_bar = Axes.bar

    def capture_bars(axis, positions, heights, **options):
        plotted[axis.get_ylabel()].extend(heights)
        return original_bar(axis, positions, heights, **options)

    monkeypatch.setattr(Axes, "bar", capture_bars)
    outputs = run_experiments(
        seed=42, cases=4, repeats=3, scenario_dir=tmp_path / "cases",
        results_dir=tmp_path / "tables", figures_dir=tmp_path / "figures",
    )
    assert (outputs.checked_cases, outputs.generated_cases, outputs.observations) == (6, 4, 24)
    summary = _read_table(outputs.summary_csv, SUMMARY_FIELDS)
    timings = _read_table(outputs.timing_csv, TIMING_FIELDS)
    assert len(summary) == 8
    assert len(timings) == 24

    collected = defaultdict(list)
    for row in timings:
        series = collected[row["scenario_id"], row["algorithm"]]
        assert int(row["repetition"]) == len(series) + 1
        assert int(row["elapsed_ns"]) > 0
        series.append(int(row["elapsed_ns"]))

    for bfs, ucs in zip(summary[::2], summary[1::2], strict=True):
        assert (bfs["algorithm"], ucs["algorithm"]) == ("BFS", "UCS")
        for key in ("scenario_id", "start_asset", "start_privilege", "goal_asset", "required_privilege",
                    "seed", "asset_count", "structure", "solution_found"):
            assert bfs[key] == ucs[key]

    for row in summary:
        durations = collected[row["scenario_id"], row["algorithm"]]
        assert len(durations) == int(row["repeats"]) == 3
        for label, aggregate in (("mean", mean), ("median", median), ("stdev", pstdev)):
            assert float(row[f"{label}_runtime_ms"]) == pytest.approx(aggregate(durations) / 1e6, abs=0.0000005)
        if row["structure"] == "unreachable":
            assert row["solution_found"] == "false"
            assert all(row[key] == "" for key in ("solution_valid", "steps", "effort", "path_states", "path_actions"))
        else:
            assert row["solution_found"] == row["solution_valid"] == "true"
            assert int(row["steps"]) == len(json.loads(row["path_actions"]))
    assert {figure.name for figure in outputs.figures} == {
        "states_expanded.png", "mean_search_runtime.png", "path_effort.png",
    }
    assert all(figure.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for figure in outputs.figures)
    assert sorted(plotted["Mean elapsed time (ms)"]) == sorted(
        float(row["mean_runtime_ms"]) for row in summary
    )
    assert sorted(plotted["Modeled effort (assigned units)"]) == sorted(
        float(row["effort"]) for row in summary if row["effort"]
    )


def test_checked_baselines_are_independently_verified():
    assert verify_checked_cases() == 6


def test_invalid_repeat_count_is_reported_before_writing_outputs(tmp_path):
    with pytest.raises(ValueError, match="Repetition count"):
        run_experiments(repeats=0, results_dir=tmp_path / "tables")
    assert not (tmp_path / "tables").exists()
