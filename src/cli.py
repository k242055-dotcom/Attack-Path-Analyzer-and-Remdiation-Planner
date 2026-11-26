"""Console interface for comparing and explaining offline model searches."""

import argparse
import sys
from pathlib import Path

from .agents import SearchResult, compare
from .environment import FIX_RECORDS, NetworkEnvironment
from .models import PRIVILEGE_LEVELS, AttackState, GoalSpecification, Remediation
from .paths import CHECKED_DIR, PROJECT_ROOT, bundled_scenarios
from .remediation import preview_fix
from .reporting import FAMILY_LABELS, FIX_LABELS, export_comparison, route_label, state_label
from .validation import load_scenario
from .verification import verify_result


def _fix(value: str) -> Remediation:
    kind, separator, record_id = value.partition(":")
    if not separator or kind not in FIX_RECORDS or not record_id or ":" in record_id:
        raise argparse.ArgumentTypeError(
            f"enter KIND:ID using one of these kinds: {', '.join(FIX_RECORDS)}"
        )
    return Remediation(kind, record_id)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, default=CHECKED_DIR / "simple_path.json", help="local JSON scenario")
    parser.add_argument("--list-scenarios", action="store_true", help="list bundled scenario paths")
    parser.add_argument("--list-fixes", action="store_true", help="list enabled fixes for the selected scenario")
    parser.add_argument("--start-asset", help="override the scenario's starting asset")
    parser.add_argument("--start-privilege", choices=PRIVILEGE_LEVELS)
    parser.add_argument("--target-asset", help="override the scenario's target asset")
    parser.add_argument("--target-privilege", choices=PRIVILEGE_LEVELS, help="minimum privilege at the target")
    parser.add_argument("--fix", type=_fix, metavar="KIND:ID", help="preview one simulated fix")
    parser.add_argument("--json-out", type=Path, metavar="FILE", help="export the query and results as JSON")
    return parser


def _show_result(result: SearchResult) -> None:
    print(f"\n{result.algorithm}  {result.message}")
    print(f"  {route_label(result, ' -> ')}")
    if result.found:
        print(f"  Steps {result.steps} | Effort {result.total_cost}")
    print(f"  Expanded {result.expanded} | Discovered {result.discovered} | Search {result.elapsed_ms:.4f} ms")
    cumulative = 0
    for index, action in enumerate(result.actions, start=1):
        cumulative += action.cost
        print(f"  {index}. {FAMILY_LABELS[action.family]} ({action.id})")
        print(f"     {action.explanation} Effort +{action.cost}, cumulative {cumulative}.")
        for condition in action.preconditions:
            print(f"     - {condition}")


def main(argv: list[str] | None = None) -> int:
    """Run the selected console operation and return a process exit code."""
    args = _parser().parse_args(argv)
    if args.list_scenarios:
        for path in bundled_scenarios():
            print(path.relative_to(PROJECT_ROOT).as_posix())
        return 0

    try:
        scenario = load_scenario(args.scenario)
        environment = NetworkEnvironment(scenario)
        if args.list_fixes:
            fixes = environment.fixes()
            for fix in fixes:
                print(f"{fix.kind}:{fix.record_id}")
            if not fixes:
                print("This scenario has no enabled remediation records.")
            return 0

        start = AttackState(
            scenario.start.asset_id if args.start_asset is None else args.start_asset,
            args.start_privilege or scenario.start.privilege_level,
        )
        goal = GoalSpecification(
            scenario.goal.asset_id if args.target_asset is None else args.target_asset,
            args.target_privilege or scenario.goal.required_privilege,
        )
        print(scenario.name)
        print(f"Start {state_label(start)} | Goal {goal.asset_id}/{goal.required_privilege} or higher")
        preview = None
        if args.fix is not None:
            preview = preview_fix(environment, start, goal, args.fix)
        results = preview.before if preview else compare(environment, start, goal)
        for result in results:
            verify_result(environment, start, goal, result)
            _show_result(result)

        if preview is not None:
            print(f"\nPreview  {FIX_LABELS[preview.fix.kind]} {preview.fix.record_id}")
            change = "Enabled to disabled." if preview.record_changed else "The record was already disabled."
            print(f"  {change}")
            if preview.removed_transitions == 0:
                print("  No modeled transition changed.")
            else:
                print(f"  Removed {preview.removed_transitions} legal action-state pairs.")
            for result, effect in zip(preview.after, preview.effects):
                _show_result(result)
                print(f"  {effect}")

        if args.json_out is not None:
            export_comparison(args.json_out, scenario.id, start, goal, results, preview)
            print(f"\nExported {args.json_out}")
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
