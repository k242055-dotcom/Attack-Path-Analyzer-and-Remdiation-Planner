"""Draw directed model connectivity with a deterministic, local layout."""

from io import BytesIO
from math import cos, pi, sin

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch

from .models import AttackState, GoalSpecification, Scenario

_INK = "#16283d"
_LINK = "#54798c"
_DISABLED = "#a1a9b4"
_START = "#126a70"
_TARGET = "#a9500e"
_PAPER = "#ffffff"
_BOTH = "#713c90"


def needs_focus(scenario: Scenario) -> bool:
    """Indicate when a neighborhood view keeps the topology readable."""
    return len(scenario.assets) > 30 or len(scenario.connections) > 80


def topology_png(
    scenario: Scenario, start: AttackState, goal: GoalSpecification, focus: str | None = None,
) -> bytes:
    """Render declared connectivity. Focus shows up to 16 direct neighbors."""
    ids = sorted(asset.id for asset in scenario.assets)
    if focus is not None:
        adjacent = {
            endpoint
            for link in scenario.connections
            if focus in (link.source_asset_id, link.destination_asset_id)
            for endpoint in (link.source_asset_id, link.destination_asset_id)
            if endpoint != focus
        }
        ids = sorted({focus, *sorted(adjacent)[:16]})
    links = [
        link for link in scenario.connections
        if link.source_asset_id in ids and link.destination_asset_id in ids
        and (focus is None or focus in (link.source_asset_id, link.destination_asset_id))
    ]
    positions = {
        asset_id: (1.40 * cos(angle), sin(angle))
        for index, asset_id in enumerate(ids)
        for angle in [pi / 2 - (2 * pi * index / len(ids))]
    }
    if len(ids) == 1:
        positions[ids[0]] = (0, 0)

    figure = Figure(figsize=(10.4, 4.5), dpi=120, facecolor=_PAPER)
    axes = figure.add_axes([0.02, 0.16, 0.96, 0.79])
    axes.set(xlim=(-2.02, 2.02), ylim=(-1.30, 1.30), aspect="equal")
    axes.axis("off")
    link_pairs = {(link.source_asset_id, link.destination_asset_id) for link in links}
    for link in sorted(links, key=lambda item: item.id):
        reverse = (link.destination_asset_id, link.source_asset_id) in link_pairs
        axes.add_patch(FancyArrowPatch(
            positions[link.source_asset_id], positions[link.destination_asset_id],
            arrowstyle="-|>", mutation_scale=12, shrinkA=9, shrinkB=9,
            connectionstyle=f"arc3,rad={0.15 if reverse else 0}",
            linewidth=1.35, linestyle="solid" if link.enabled else "dashed",
            color=_LINK if link.enabled else _DISABLED, alpha=0.88 if link.enabled else 0.72,
        ))

    for asset_id, (x, y) in positions.items():
        is_start = asset_id == start.asset_id
        is_goal = asset_id == goal.asset_id
        color = _INK
        if is_start and is_goal:
            color = _BOTH
        elif is_start:
            color = _START
        elif is_goal:
            color = _TARGET
        axes.scatter([x], [y], s=150 if is_start or is_goal else 92, zorder=4, color=color,
                     edgecolors=_PAPER, linewidths=1.5)
        label = f"{asset_id[:15]}…" if len(asset_id) > 16 else asset_id
        axes.text(x * 1.14, y * 1.15 + (0.12 if len(ids) == 1 else 0), label, color=_INK,
                  va="center", ha="center", fontsize=8 if len(ids) > 14 else 10, fontweight="medium",
                  parse_math=False, zorder=5)

    legend = [
        Line2D([0], [0], color=_LINK, label="Enabled link"),
        Line2D([0], [0], color=_DISABLED, linestyle="dashed", label="Disabled link"),
        Line2D([0], [0], color=_START, marker="o", linestyle="none", label="Start"),
        Line2D([0], [0], color=_TARGET, marker="o", linestyle="none", label="Goal"),
    ]
    if start.asset_id == goal.asset_id:
        legend.append(Line2D([0], [0], color=_BOTH, marker="o", linestyle="none", label="Start and goal"))
    figure.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.045),
                  ncols=len(legend), fontsize=9, frameon=False, labelcolor=_INK)
    output = BytesIO()
    FigureCanvasAgg(figure).print_png(output)
    return output.getvalue()
