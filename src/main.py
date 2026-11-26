"""Streamlit dashboard for synthetic routes and remediation comparisons."""

import csv
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

import streamlit as st

from src.agents import SearchResult, compare
from src.environment import NetworkEnvironment
from src.experiments import SUMMARY_FILENAME, TIMINGS_FILENAME
from src.models import AttackState, GoalSpecification, Scenario
from src.network_plot import needs_focus, topology_png
from src.paths import CHECKED_DIR, FIGURES_DIR, PROJECT_ROOT, RESULTS_DIR, bundled_scenarios
from src.remediation import preview_fix
from src.reporting import FAMILY_LABELS, FIX_LABELS, route_label
from src.validation import MAX_BYTES, ValidationError, loads_scenario
from src.verification import verify_result
from src.visualise import CHARTS


def _case_label(path: Path) -> str:
    if path.parent == CHECKED_DIR:
        return path.stem.replace("_", " ").title()
    return f"Generated {path.stem.removeprefix('case-')}"


def _load_selection() -> tuple[Scenario, str] | None:
    st.header("Scenario")
    source = st.radio("Scenario source", ["Bundled", "Local JSON"], horizontal=True)
    try:
        if source == "Bundled":
            cases = bundled_scenarios()
            if not cases:
                st.info("No bundled cases are available. Select Local JSON to load a case.")
                return None
            default = next((index for index, path in enumerate(cases) if path.stem == "simple_path"), 0)
            path = st.selectbox("Bundled case", cases, index=default, format_func=_case_label, key="bundled_case")
            with path.open("rb") as file:
                content = file.read(MAX_BYTES + 1)
        else:
            upload = st.file_uploader("Upload a synthetic scenario", type=["json"])
            if upload is None:
                return None
            content = upload.getvalue()
        return loads_scenario(content), sha256(content).hexdigest()
    except (OSError, ValidationError) as exc:
        st.error("Scenario could not be loaded.")
        st.code(str(exc), language=None, wrap_lines=True)
        return None


def _query(environment: NetworkEnvironment, case_key: str) -> tuple[AttackState, GoalSpecification]:
    scenario = environment.scenario
    names = {asset.id: asset.label for asset in scenario.assets}
    counts = Counter(names.values())
    labels = {asset: f"{name} ({asset})" if counts[name] > 1 else name for asset, name in names.items()}
    asset_ids = environment.asset_ids
    levels = scenario.privilege_levels
    st.header("Start and goal")
    start_asset = st.selectbox("Starting asset", asset_ids, index=asset_ids.index(scenario.start.asset_id),
                               format_func=labels.__getitem__, key=f"{case_key}:source")
    start_level = st.selectbox("Initial privilege", levels, index=levels.index(scenario.start.privilege_level),
                               key=f"{case_key}:initial")
    goal_asset = st.selectbox("Target asset", asset_ids, index=asset_ids.index(scenario.goal.asset_id),
                              format_func=labels.__getitem__, key=f"{case_key}:target")
    goal_level = st.selectbox("Required target privilege", levels, index=levels.index(scenario.goal.required_privilege),
                              key=f"{case_key}:required")
    return AttackState(start_asset, start_level), GoalSpecification(goal_asset, goal_level)


def _explorer(environment: NetworkEnvironment, start: AttackState, goal: GoalSpecification) -> None:
    scenario = environment.scenario
    st.subheader("Network explorer")
    st.text(scenario.name)
    st.text(scenario.description)
    asset_count, link_count, rule_count = st.columns(3)
    asset_count.metric("Assets", len(scenario.assets))
    link_count.metric("Directed links", len(scenario.connections))
    rule_count.metric("Declared action rules", len(scenario.actions))
    st.caption("Arrows show declared connectivity. Rule conditions determine which state transitions are legal.")
    focus = None
    if needs_focus(scenario):
        focus = st.selectbox("Focus asset", environment.asset_ids, index=environment.asset_ids.index(start.asset_id))
        st.caption("The diagram shows up to 16 direct neighbors. The declared records include the full network.")
    st.image(topology_png(scenario, start, goal, focus), width="stretch")
    st.caption(f"Privilege order  {' < '.join(scenario.privilege_levels)}")

    with st.expander("Declared records"):
        groups = {
            "Assets": scenario.assets,
            "Services": scenario.services,
            "Connections": scenario.connections,
            "Weaknesses": scenario.weaknesses,
            "Permissions": scenario.permissions,
            "Credential capabilities": scenario.credentials,
            "Action rules": scenario.actions,
        }
        group = st.selectbox("Record type", tuple(groups))
        records = []
        for record in groups[group]:
            fields = asdict(record)
            if group == "Credential capabilities":
                fields["authorizations"] = ", ".join(
                    f"{item.service_id} → {item.granted_privilege}" for item in record.authorizations
                )
            records.append(fields)
        if records:
            st.dataframe(records, hide_index=True, width="stretch")
        else:
            st.info(f"This case has no {group.lower()} records.")


def _result_card(result: SearchResult) -> None:
    st.caption(result.message)
    st.code(route_label(result), language=None, wrap_lines=True)
    steps, cost, expanded, runtime = st.columns(4)
    steps.metric("Steps", "—" if result.steps is None else result.steps)
    cost.metric("Effort", "—" if result.total_cost is None else result.total_cost)
    expanded.metric("Expanded", result.expanded)
    runtime.metric("Search ms", f"{result.elapsed_ms:.4f}")
    st.caption(f"Discovered states  {result.discovered}")


def _route_explanation(result: SearchResult) -> None:
    if not result.actions:
        return
    with st.expander(f"{result.algorithm} route explanation"):
        cumulative = 0
        for step, action in enumerate(result.actions, start=1):
            cumulative += action.cost
            with st.container(border=True):
                st.markdown(f"**{step}. {FAMILY_LABELS[action.family]}**")
                st.text(action.explanation)
                st.caption(f"Effort +{action.cost} · Cumulative {cumulative}")
                st.markdown("\n".join(f"- {condition}" for condition in action.preconditions))


def _comparison(
    environment: NetworkEnvironment, case_key: str, start: AttackState, goal: GoalSpecification,
) -> None:
    st.subheader("Algorithm comparison")
    st.caption("BFS minimizes the number of actions. UCS minimizes total modeled effort.")
    key = (case_key, start, goal)
    if st.button("Compare BFS and UCS", type="primary", key="compare_agents"):
        results = compare(environment, start, goal)
        for result in results:
            verify_result(environment, start, goal, result)
        st.session_state["comparison_result"] = (key, results)
    saved = st.session_state.get("comparison_result")
    if saved is None or saved[0] != key:
        st.info("Run the comparison to see routes and search metrics for the configured query.")
        return
    columns = st.columns(2)
    for column, result in zip(columns, saved[1]):
        with column:
            st.subheader(result.algorithm)
            _result_card(result)
    for result in saved[1]:
        _route_explanation(result)


def _remediation(
    environment: NetworkEnvironment, case_key: str, start: AttackState, goal: GoalSpecification,
) -> None:
    st.subheader("Remediation planner")
    st.caption("Preview one declared record change and compare both agents with the baseline.")
    fixes = environment.fixes()
    if not fixes:
        st.info("There are no enabled remediation records in this scenario.")
        return
    fix = st.selectbox("Record to change", fixes, format_func=lambda item: f"{FIX_LABELS[item.kind]} · {item.record_id}",
                       key=f"{case_key}:fix")
    key = (case_key, start, goal, fix)
    run, discard = st.columns(2)
    if run.button("Preview fix", type="primary", key="preview_fix"):
        st.session_state["fix_result"] = (key, preview_fix(environment, start, goal, fix))
    saved = st.session_state.get("fix_result")
    current = saved is not None and saved[0] == key
    if discard.button("Discard preview", disabled=not current, key="discard_fix"):
        st.session_state.pop("fix_result", None)
        return
    if not current:
        return
    preview = saved[1]
    st.text(f"{FIX_LABELS[fix.kind]} · {fix.record_id} · Enabled → disabled")
    if preview.removed_transitions == 0:
        st.info("No modeled transition changed.")
    else:
        st.caption(f"Removed {preview.removed_transitions} legal action-state pairs across the model.")
    for before, after, effect in zip(preview.before, preview.after, preview.effects):
        st.subheader(before.algorithm)
        st.info(effect)
        baseline, updated = st.columns(2)
        with baseline:
            st.markdown("**Baseline**")
            _result_card(before)
        with updated:
            st.markdown("**With fix**")
            _result_card(after)


def _experiments() -> None:
    st.subheader("Stored experiments")
    summary = RESULTS_DIR / SUMMARY_FILENAME
    try:
        content = summary.read_bytes()
        reader = csv.DictReader(content.decode("utf-8").splitlines(), strict=True)
        rows = list(reader)
        if (
            not rows
            or "scenario_id" not in (reader.fieldnames or [])
            or any(None in row or None in row.values() for row in rows)
        ):
            raise ValueError("Expected a results table with a scenario_id column and complete rows.")
    except FileNotFoundError:
        st.info("Run the experiment command to generate the results table and figures.")
        st.code("python -m src.experiments --seed 42 --cases 20 --repeats 10", language="bash")
        return
    except (OSError, ValueError, csv.Error) as exc:
        st.warning("The stored results table could not be loaded.")
        st.code(str(exc), language=None, wrap_lines=True)
        return

    st.dataframe(rows, width="stretch", hide_index=True)
    exports = st.columns(2)
    exports[0].download_button("Download summary CSV", content, summary.name, "text/csv")
    raw = RESULTS_DIR / TIMINGS_FILENAME
    try:
        exports[1].download_button("Download raw timings", raw.read_bytes(), raw.name, "text/csv")
    except OSError:
        exports[1].caption("Raw timings are unavailable.")
    chart_paths = {title: filename for _, title, _, filename in CHARTS}
    metric = st.selectbox("Experiment chart", tuple(chart_paths))
    figure = FIGURES_DIR / chart_paths[metric]
    try:
        data = figure.read_bytes()
        st.image(data, width="stretch", caption=metric)
        st.download_button("Download selected chart", data, figure.name, "image/png")
    except OSError:
        st.info("This chart is unavailable. Regenerate it with the experiment command.")


def _help() -> None:
    st.subheader("Help and limitations")
    st.markdown(
        "Select a bundled case or load a version 1 JSON file containing fictitious assets and explicit "
        "rules. The target is reached when the route meets or exceeds the required privilege.\n\n"
        "Effort is an assigned integer from 1 to 5 per action. A missing route applies to the modeled "
        "rules and the selected query. Credential capabilities are available only at their declared source.\n\n"
        "The standard experiment regenerates 20 cases from seed 42 and records 10 timings per agent and case. "
        "Logical outcomes are repeatable. Timings vary by run and machine."
    )
    schema = PROJECT_ROOT / "docs" / "scenario-schema.md"
    if schema.is_file():
        st.download_button("Download scenario schema guide", schema.read_bytes(), schema.name, "text/markdown")


def main() -> None:
    """Run the local dashboard."""
    st.set_page_config(page_title="Attack-Path Analyzer and Remediation Planner", layout="wide")
    st.title("Attack-Path Analyzer and Remediation Planner")
    st.caption("AL-2002 Artificial Intelligence Laboratory · FAST-NUCES Karachi · Fall 2026")
    st.markdown("Compare graph-search routes through a synthetic network and preview changes to the model offline.")
    with st.sidebar:
        selection = _load_selection()
        if selection is not None:
            scenario, case_key = selection
            environment = NetworkEnvironment(scenario)
            start, goal = _query(environment, case_key)
    explore, comparison, fixes, experiments, help_tab = st.tabs(
        ["Network", "Compare", "Remediation", "Experiments", "Help"]
    )
    if selection is None:
        for tab in (explore, comparison, fixes):
            tab.info("Load a synthetic scenario to use this section.")
    else:
        with explore:
            _explorer(environment, start, goal)
        with comparison:
            _comparison(environment, case_key, start, goal)
        with fixes:
            _remediation(environment, case_key, start, goal)
    with experiments:
        _experiments()
    with help_tab:
        _help()


if __name__ == "__main__":
    main()
