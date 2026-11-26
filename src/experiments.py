"""Verify checked cases and benchmark BFS and UCS on paired generated instances."""

import argparse
import csv
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import mean, median, pstdev
from tempfile import TemporaryDirectory
from typing import Any

from .agents import BFSAgent, SearchResult, UCSAgent, compare
from .environment import NetworkEnvironment
from .models import Scenario
from .paths import CHECKED_DIR, DATA_DIR, FIGURES_DIR, GENERATED_DIR, RESULTS_DIR
from .scenario_generator import DEFAULT_CASES, DEFAULT_SEED, generate_to_directory
from .validation import load_scenario
from .verification import verify_result
from .visualise import write_experiment_charts

DEFAULT_REPEATS = 10
SUMMARY_FILENAME = "search_summary.csv"
TIMINGS_FILENAME = "search_timings.csv"
SUMMARY_FIELDS = (
    "scenario_id", "seed", "generator_version", "generated_cases", "structure", "asset_count",
    "algorithm", "start_asset", "start_privilege", "goal_asset", "required_privilege",
    "solution_found", "solution_valid", "steps", "effort", "states_expanded", "states_discovered",
    "path_states", "path_actions", "mean_runtime_ms", "median_runtime_ms", "stdev_runtime_ms", "repeats",
)
TIMING_FIELDS = ("scenario_id", "algorithm", "repetition", "elapsed_ns")

Row = dict[str, str | int | None]


@dataclass(frozen=True)
class ExperimentOutputs:
    """Paths and counts for a successful run."""

    checked_cases: int
    generated_cases: int
    observations: int
    summary_csv: Path
    timing_csv: Path
    figures: tuple[Path, ...]


def _read_checked_expectations() -> dict[str, Any]:
    path = DATA_DIR / "checked-expectations.json"
    expectations = json.loads(path.read_text(encoding="utf-8"))
    names = {item.stem for item in CHECKED_DIR.glob("*.json")}
    if not isinstance(expectations, dict) or len(expectations) != 6 or set(expectations) != names:
        raise ValueError(f"{path} must cover exactly the six bundled checked scenarios.")
    return expectations


def verify_checked_cases() -> int:
    """Compare checked routes with independent hand-derived expectations, outside recorded timing."""
    expectations = _read_checked_expectations()
    for scenario_id, expected in expectations.items():
        scenario = load_scenario(CHECKED_DIR / f"{scenario_id}.json")
        environment = NetworkEnvironment(scenario)
        for result in compare(environment, scenario.start, scenario.goal):
            verify_result(environment, scenario.start, scenario.goal, result)
            observed = {"action_ids": [action.id for action in result.actions], "steps": result.steps,
                        "effort": result.total_cost}
            if not isinstance(expected, dict) or observed != expected.get(result.algorithm):
                raise ValueError(f"{scenario.id} {result.algorithm} differs from its checked expectation: {observed}.")
    return len(expectations)


def _measure(scenario: Scenario, case_position: int, repeats: int) -> dict[str, list[SearchResult]]:
    environment = NetworkEnvironment(scenario)
    agents = (BFSAgent(environment), UCSAgent(environment))
    records: dict[str, list[SearchResult]] = {agent.name: [] for agent in agents}
    for repetition in range(1, repeats + 1):
        order = agents if (case_position + repetition) % 2 == 0 else agents[::-1]
        for agent in order:
            records[agent.name].append(agent.search(scenario.start, scenario.goal))

    for algorithm, attempts in records.items():
        first = attempts[0]
        verify_result(environment, scenario.start, scenario.goal, first)
        expected = replace(first, elapsed_ns=0)
        if any(replace(attempt, elapsed_ns=0) != expected for attempt in attempts[1:]):
            raise ValueError(f"{scenario.id} {algorithm} changed its logical result across repetitions.")
    bfs, ucs = records["BFS"][0], records["UCS"][0]
    if bfs.found != ucs.found:
        raise ValueError(f"{scenario.id}: BFS and UCS disagree on modeled reachability.")
    if bfs.found and (bfs.steps > ucs.steps or ucs.total_cost > bfs.total_cost):
        raise ValueError(f"{scenario.id}: BFS or UCS violates its objective relative to the other route.")
    return records


def _summarize(scenario: Scenario, attempts: list[SearchResult], case_count: int) -> Row:
    first = attempts[0]
    durations = [attempt.elapsed_ns for attempt in attempts]
    summary = {
        "scenario_id": scenario.id,
        "seed": scenario.metadata["seed"],
        "generator_version": scenario.metadata["generator_version"],
        "generated_cases": case_count,
        "structure": scenario.metadata["pattern"],
        "asset_count": len(scenario.assets),
        "algorithm": first.algorithm,
        "start_asset": scenario.start.asset_id,
        "start_privilege": scenario.start.privilege_level,
        "goal_asset": scenario.goal.asset_id,
        "required_privilege": scenario.goal.required_privilege,
        "solution_found": str(first.found).lower(),
        "solution_valid": "true" if first.found else None,
        "steps": first.steps,
        "effort": first.total_cost,
        "states_expanded": first.expanded,
        "states_discovered": first.discovered,
        "path_states": json.dumps([state.key() for state in first.states], separators=(",", ":")) if first.found else None,
        "path_actions": json.dumps([action.id for action in first.actions], separators=(",", ":")) if first.found else None,
        "mean_runtime_ms": f"{mean(durations) / 1_000_000:.6f}",
        "median_runtime_ms": f"{median(durations) / 1_000_000:.6f}",
        "stdev_runtime_ms": f"{pstdev(durations) / 1_000_000:.6f}",
        "repeats": len(attempts),
    }
    return summary


def _write_csv(path: Path, fields: tuple[str, ...], rows: Iterable[Mapping[str, str | int | None]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_experiments(
    seed: int = DEFAULT_SEED, cases: int = DEFAULT_CASES, repeats: int = DEFAULT_REPEATS, *,
    scenario_dir: Path = GENERATED_DIR, results_dir: Path = RESULTS_DIR, figures_dir: Path = FIGURES_DIR,
) -> ExperimentOutputs:
    """Generate inputs, verify paths, measure both agents and publish the CSVs and figures."""
    if type(repeats) is not int or not 1 <= repeats <= 100:
        raise ValueError("Repetition count must be an integer from 1 to 100.")
    checked = verify_checked_cases()
    paths = generate_to_directory(seed, cases, scenario_dir)
    summary: list[Row] = []
    timing_rows: list[Row] = []
    for case_position, path in enumerate(paths, start=1):
        scenario = load_scenario(path)
        results = _measure(scenario, case_position, repeats)
        for algorithm, attempts in results.items():
            summary.append(_summarize(scenario, attempts, cases))
            timing_rows.extend(
                {"scenario_id": scenario.id, "algorithm": algorithm,
                 "repetition": repetition, "elapsed_ns": result.elapsed_ns}
                for repetition, result in enumerate(attempts, start=1)
            )

    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    summary_csv, timing_csv = results_dir / SUMMARY_FILENAME, results_dir / TIMINGS_FILENAME
    # Finish all rendering and CSV generation before replacing existing experiment outputs.
    with TemporaryDirectory(dir=results_dir) as table_stage, TemporaryDirectory(dir=figures_dir) as figure_stage:
        staged_summary, staged_timing = Path(table_stage) / SUMMARY_FILENAME, Path(table_stage) / TIMINGS_FILENAME
        _write_csv(staged_summary, SUMMARY_FIELDS, summary)
        _write_csv(staged_timing, TIMING_FIELDS, timing_rows)
        staged_figures = write_experiment_charts(summary, Path(figure_stage))
        figures = tuple(path.replace(figures_dir / path.name) for path in staged_figures)
        staged_timing.replace(timing_csv)
        staged_summary.replace(summary_csv)
    return ExperimentOutputs(checked, len(paths), len(timing_rows), summary_csv, timing_csv, figures)


def main(argv: list[str] | None = None) -> None:
    """Run the reproducible comparison from a local command prompt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--cases", type=int, default=DEFAULT_CASES)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--scenario-dir", type=Path, default=GENERATED_DIR)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--figures-dir", type=Path, default=FIGURES_DIR)
    args = parser.parse_args(argv)
    try:
        outputs = run_experiments(
            args.seed, args.cases, args.repeats,
            scenario_dir=args.scenario_dir, results_dir=args.results_dir, figures_dir=args.figures_dir,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(f"Verified {outputs.checked_cases} checked cases against hand-computed baselines.")
    print(f"Recorded {outputs.observations} timed searches across {outputs.generated_cases} generated cases.")
    print(f"Summary: {outputs.summary_csv}\nRaw timings: {outputs.timing_csv}")
    print("Figures: " + ", ".join(str(path) for path in outputs.figures))


if __name__ == "__main__":
    main()
