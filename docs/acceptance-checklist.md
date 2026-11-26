# Implementation and acceptance checklist

## Source review

The workspace contains the two matching proposal editions and the Fall 2026 AL-2002 guidelines in `reference/`. The build request calls this directory `refence/`. Preserve the existing directory and its three original files. Deliver the application at the workspace root. The four-page proposal PDF fits the three- to four-page requirement. No separate report template was supplied.

The project title is **Attack-Path Analyzer and Remediation Planner**, proposed for AL-2002 Artificial Intelligence Laboratory, FAST-NUCES Karachi Campus, Fall 2026. The proposal lists Muhammad Mutahir (24K-2005, search and integration, 34%), Syed Muhammad Muzamil (24K-2000, dashboard and visualization, 33%), and Muhammad Abdullah (24K-2055, model and experiments, 33%). Its submission date is 21 October 2026. The shares describe proposed work. It is an own-idea proposal under Part B — Applied / Data, subject to instructor approval and category confirmation.

**Instructor clarification is required.** The guideline heading permits groups of up to three while Section 1 limits them to two. Preserve the three proposed members. The first four milestones each say “Build week 1”; the proposal assigns no distinct calendar dates to them. Section fields and the repository URL are blank. Retain the milestones and leave institutional, submission, and individual contribution claims unverified until supported.

## Build gates

| Gate | Acceptance condition | Planned verification |
| --- | --- | --- |
| 1. Sources | Read the original Markdown and PDF proposal, guidelines DOCX, and master build prompt. Document conflicts and extract requirements. | Compare proposal editions and check the original file hashes before delivery. |
| 2. Model | Versioned bounded JSON, actionable validation errors, stable IDs, `guest < user < admin`, directed reachability, integer effort 1–5 and source-local credential capabilities. The model is fully declared and synthetic. | Validate default endpoints and reject malformed JSON, invalid references, contradictory rules, invalid privileges and costs. Check allow and deny conditions for each of the three transition families. |
| 3. Search | Hand-written FIFO BFS and heap-based UCS implement one agent interface and share a deterministic environment. Goal testing accepts equal or higher privileges. | Independently replay paths and compare with known optima. Exercise ties, cycles, stale UCS entries, zero-action goals, unreachable goals and expansion counting. |
| 4. Checked cases | Simple, cost trade-off, unreachable, cyclic, blocking-fix, and alternate-route scenarios include independent hand-computed expectations. | Assert exact paths, costs, and steps where applicable. Verify missing path metrics and all six checked cases. |
| 5. Remediation | Preview one weakness disable, credential or permission revoke, or directed connection block. Compare both agents before and after with stable record IDs and an immutable baseline. | Test complete blocking, alternate routes, unchanged routes, and baseline identity after previews. |
| 6. Generation | Seed 42 generates 20 reproducible synthetic cases of 10–30 assets, with meaningful reachability, structure and cost variation. | Validate every scenario and compare canonical JSON from consecutive runs. |
| 7. Experiments | Identical problem instances, 10 timings per algorithm per generated case, 400 recorded searches, search-only timing, stable CSV order and missing metrics for unreachable goals. | Re-run `python -m src.experiments --seed 42 --cases 20 --repeats 10`. Compare logical results across runs. Check the raw and aggregate CSVs and charts for expansions, mean runtime and reported path effort. |
| 8. Interfaces | Local Streamlit dashboard and CLI expose scenario loading, start/goal selection, comparison, explanations and remediation. The dashboard displays the declared graph and stored experiments. | Start the dashboard, run a bundled case and a preview from the CLI, and check missing or invalid inputs. |
| 9. Documentation | README, architecture and flow diagrams, schema, compliance audit, optional lab-validation notes, viva guide, preserved proposal and evidence-based report. | Check root commands, report-to-CSV agreement, required PDF and Markdown pairs, and 3–4 proposal / 8–10 report pages. |
| 10. Root verification | All required directories and dependencies are present; application, tests and experiments run from the root. | Run `python -m pytest -q`, the standard experiment, `python -m src.cli --scenario data/scenarios/checked/simple_path.json` and `streamlit run src/main.py`. Record actual outcomes. |

## Academic verification

- Map Lab 01–02 OOP and seeded reproducibility, Lab 03 PEAS and environment classification, and Lab 04 original search implementations to actual files and functions.
- Cite the supplied materials, software dependencies and AI assistance. Confirm the report reflects observed results and recorded testing. Record the optional container observation status separately.
- Keep instructor approval, group registration, genuine contributions and commits, publication, independent clean-clone checks, Classroom submission and individual viva work pending until verified by the responsible students.
