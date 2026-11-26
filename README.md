# Attack-Path Analyzer and Remediation Planner

This offline educational application compares routes in a synthetic network. Pick an assumed starting asset and privilege and a target with a required privilege. Breadth-first search (BFS) finds a route with the fewest actions. Uniform-cost search (UCS) finds a route with the least assigned effort. The Streamlit dashboard and terminal interface show which declared conditions permit each action and how a simulated fix changes the result.

**AL-2002 Artificial Intelligence Laboratory, Fall 2026**  
FAST — National University of Computer and Emerging Sciences, Karachi Campus

## Setup

Use Python 3.11 or 3.12 and run commands from the project root. The installation step uses the package index. The installed application, tests and experiments run locally.

### Windows Command Prompt (cmd.exe)

```bat
py -3.12 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python --version
```

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"
python --version
```

Linux with Python 3.12 available

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python --version
```

## Run the application

If the packages are already installed in `.venv`, this command launches the dashboard from either Windows shell without activating the environment.

```bat
.\.venv\Scripts\python.exe -m streamlit run src/main.py
```

With the virtual environment active, use this command.

```bash
python -m streamlit run src/main.py
```

Open the local address printed by Streamlit, normally `http://127.0.0.1:8501`. Choose a bundled scenario or load a synthetic JSON file, then set the start and goal in the sidebar. The Network tab shows declared links and conditions. Use Compare to run BFS and UCS, and Remediation to preview one record change and discard it when finished.

The console uses the same validated model and accepts query overrides, fix previews and a JSON export.

```bash
python -m src.cli --scenario data/scenarios/checked/simple_path.json
python -m src.cli --list-scenarios
python -m src.cli --scenario data/scenarios/checked/blocking_fix.json --list-fixes
python -m src.cli --scenario data/scenarios/checked/blocking_fix.json --fix block_connection:link_entry_archive --json-out tmp/blocking-preview.json
python -m src.cli --help
```

## Verify and reproduce

```bash
python -m pytest -q
python -m src.scenario_generator --seed 42 --cases 20
python -m src.experiments --seed 42 --cases 20 --repeats 10
```

The experiment command verifies six checked cases, regenerates the 20 generated inputs, and collects 400 search-only measurements. Stable logical results include reachability, paths, effort and counts of expanded states. Runtime measurements vary by run. The dashboard reads saved results and provides local downloads.

| Location | Contents |
| --- | --- |
| `data/scenarios/checked/` | Six small checked JSON models |
| `data/checked-expectations.json` | Hand-derived expectations for the six cases |
| `data/scenarios/generated/` | Deterministic synthetic cases for the standard run |
| `outputs/results/search_summary.csv` | Per-case and per-algorithm metrics |
| `outputs/results/search_timings.csv` | Individual timed observations |
| `outputs/figures/` | Three comparison charts generated from the measured results |
| `docs/` | Proposal, report, schema, architecture, viva and compliance guide |

The [report](docs/report.md) discusses the delivered run and its timing snapshot. Run `python -m src.report_document` to render the report Markdown and its referenced charts to PDF.

## How it works

The validator builds immutable records from versioned JSON. The environment enforces every declared transition rule and ranks privileges as `guest < user < admin`. The agents share that environment. BFS uses a FIFO queue and remembers the first parent of each discovered state. UCS pops the least cumulative effort from a heap and replaces a parent whenever it finds a strictly cheaper route. Both can explain the action sequence and replay it through the environment.

A preview constructs a new environment with one weakness, credential, permission or directed connection disabled. Both agents rerun on that model using the original query. See the [architecture](docs/architecture.md) and [scenario schema](docs/scenario-schema.md).

## Data and interpretation

Bundled data are original synthetic coursework fixtures and generated variations. No external dataset or dataset URL applies. The supplied coursework materials specify no redistribution license. The pinned third-party tools retain their own licenses.

Use fictional assets and symbolic credential capabilities in a scenario. Each route describes the behavior of explicitly declared rules. Costs are assigned teaching units. An unreachable result means the model contains no permitted route for the chosen query. Real configurations can differ from the model, and evaluating them is outside the scope of the application. The search uses local records throughout.

## Academic status

The original proposal lists **21 October 2026** as the submission date and identifies an own idea under the proposed **Part B — Applied / Data** category. Instructor approval and category acceptance are unverified.

| Proposed member | Roll number | Proposed responsibility | Proposed share |
| --- | --- | --- | --- |
| Muhammad Mutahir | 24K-2005 | Search algorithms, integration and repository coordination | 34% |
| Syed Muhammad Muzamil | 24K-2000 | Dashboard, visualization and route explanations | 33% |
| Muhammad Abdullah | 24K-2055 | Environment model, scenarios and experiments | 33% |

OpenAI Codex assisted with the local implementation, tests, experiments and documentation. Individual student authorship remains unverified. The proposal lists three students, the guideline heading allows up to three, and Section 1 says at most two. See the [compliance notes](docs/compliance-notes.md) for the instructor clarification and submission steps.
