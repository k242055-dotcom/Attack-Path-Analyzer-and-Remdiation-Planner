"""Render the experiment comparisons to local PNG files."""

from collections.abc import Mapping, Sequence
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

CHARTS = (
    ("states_expanded", "States Expanded", "Expanded states", "states_expanded.png"),
    ("mean_runtime_ms", "Mean Search Runtime", "Mean elapsed time (ms)", "mean_search_runtime.png"),
    ("effort", "Path Effort Cost", "Modeled effort (assigned units)", "path_effort.png"),
)

MetricRow = Mapping[str, str | int | float | None]


def _draw_chart(
    rows: Sequence[MetricRow], metric: str, title: str, units: str, output: Path,
) -> None:
    cases = list(dict.fromkeys(row["scenario_id"] for row in rows))
    values = {
        (row["scenario_id"], row["algorithm"]): None if row[metric] is None else float(row[metric])
        for row in rows
    }
    figure = Figure(figsize=(max(7.6, len(cases) * 0.46), 3.45), facecolor="white")
    FigureCanvasAgg(figure)
    axis = figure.subplots()
    figure.subplots_adjust(left=0.095, right=0.98, top=0.76, bottom=0.28)
    figure.suptitle(f"{title} — BFS versus UCS", color="#182b43", fontsize=15, fontweight="bold", y=0.965)
    axis.set_ylabel(units, color="#21364f", fontsize=9.5)

    width = 0.34
    for algorithm, color, shift in (("BFS", "#245a95", -width / 2), ("UCS", "#0b826c", width / 2)):
        observations = [(index + shift, values[case, algorithm]) for index, case in enumerate(cases)]
        axis.bar(
            [position for position, value in observations if value is not None],
            [value for _, value in observations if value is not None],
            width=width, color=color, label=algorithm, zorder=3,
        )
    missing = [
        index for index, case in enumerate(cases)
        if values[case, "BFS"] is None and values[case, "UCS"] is None
    ]
    if missing:
        axis.scatter(
            missing, [0.86] * len(missing), transform=axis.get_xaxis_transform(),
            color="#687687", marker="x", s=32, label="No modeled route", zorder=4,
        )

    axis.set_xticks(range(len(cases)), labels=cases, rotation=47, ha="right", fontsize=8.5)
    axis.set_xlim(-0.6, len(cases) - 0.4)
    axis.set_ylim(bottom=0)
    axis.set_xlabel("Generated scenario", color="#21364f", fontsize=9.5, labelpad=6)
    axis.yaxis.set_major_locator(MaxNLocator(nbins=6, integer=metric != "mean_runtime_ms"))
    axis.tick_params(length=0, colors="#33465d", axis="both")
    axis.grid(axis="y", color="#e1e7ed", linewidth=0.8)
    axis.set_axisbelow(True)
    for spine in axis.spines.values():
        spine.set_visible(False)
    handles, labels = axis.get_legend_handles_labels()
    order = sorted(range(len(labels)), key=lambda index: (labels[index] not in ("BFS", "UCS"), labels[index]))
    figure.legend(
        [handles[index] for index in order], [labels[index] for index in order],
        loc="upper center", bbox_to_anchor=(0.5, 0.89), frameon=False, ncols=len(labels), fontsize=9,
    )
    figure.savefig(output, dpi=160)


def write_experiment_charts(rows: Sequence[MetricRow], figure_dir: Path) -> tuple[Path, ...]:
    """Generate three charts directly from the measured comparison rows."""
    figure_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for metric, title, units, filename in CHARTS:
        output = figure_dir / filename
        _draw_chart(rows, metric, title, units, output)
        outputs.append(output)
    return tuple(outputs)
