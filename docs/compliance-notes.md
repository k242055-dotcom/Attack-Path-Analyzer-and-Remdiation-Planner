# AL-2002 compliance notes

**Instructor clarification required.** The guideline heading says groups of up to three. Section 1 says groups of at most two, and subsequent requirements refer to both members. The original proposal lists three students. The authorship and team records need instructor review before submission.

The proposal is dated 21 October 2026 and labels the project an own idea proposed under Part B — Applied / Data. Instructor approval and category acceptance are unverified. The four milestones labeled “Build week 1” cover model/fixtures, search, dashboard/fixes, and experiments/lab checks. The wording leaves their dates and relative order unspecified. The fifth milestone refers to course Week 15. The proposal preserves those intentions and labels.

The reference directory in this workspace is `reference/`. It contains the original proposal in Markdown and PDF, and the AL-2002 guidelines in DOCX. The proposal PDF uses the supplied template and has four pages. The workspace contained no separate report template, so the final report follows the guideline's required content and length.

## Proposed responsibilities

| Student | Roll number | Proposal allocation | Proposed share | Verified personal contribution |
| --- | --- | --- | --- | --- |
| Muhammad Mutahir | 24K-2005 | Search, integration, repository coordination | 34% | Unverified |
| Syed Muhammad Muzamil | 24K-2000 | Dashboard and visualization | 33% | Unverified |
| Muhammad Abdullah | 24K-2055 | Rules, scenarios, experiments and optional lab checks | 33% | Unverified |

OpenAI Codex assisted with the local project build. The allocation records the proposal and requires revision against genuine contribution evidence before submission.

## Guideline mapping

| Requirement | Implementation location | Verification command or evidence | Status |
| --- | --- | --- | --- |
| Labs 01–02, Python and OOP | `src/models.py`, `src/environment.py`, `src/agents.py` | Inspect frozen records, environment indices, abstract agent and overriding search methods. See [architecture](architecture.md). | Implemented |
| Labs 01–02, reproducible random source | `src/scenario_generator.py` | `python -m src.scenario_generator --seed 42 --cases 20` and deterministic generation tests | Implemented |
| Lab 03, PEAS, environment and agent classification | `docs/report.md`, `src/environment.py`, `src/agents.py` | Compare the formal model with validation, goal and successor tests | Implemented |
| Lab 04, original core AI method and same-instance alternative | `src/agents.py` | Inspect the FIFO queue and minimum-cost heap. Check `python -m pytest -q`. | Implemented |
| Lab 04, path, cost and expansion counts | `src/agents.py`, `src/verification.py`, `data/checked-expectations.json` | Independently replay legal paths and assert hand-derived optima in tests | Implemented |
| Proposal scope, three transition families and three fix categories | `src/environment.py`, `src/remediation.py` | Matched and denied preconditions, route removal, alternate route and immutability tests | Implemented |
| Controlled experiment and comparison | `src/experiments.py`, `outputs/results/`, `outputs/figures/` | `python -m src.experiments --seed 42 --cases 20 --repeats 10` | Implemented |
| Error handling and usable interface | `src/cli.py`, `src/main.py`, `src/validation.py` | CLI and dashboard startup plus invalid, missing and unreachable inputs in tests | Implemented |
| Modular project, dependencies, README, limitations and ethics | `src/`, `requirements.txt`, `README.md`, `docs/report.md` | Inspect pinned packages and reproducing commands | Implemented |
| Proposal and report in Markdown and PDF | `docs/proposal.md`, `docs/proposal.pdf`, `docs/report.md`, `docs/report.pdf` | Check document content, proposal and report page counts and rendered figures | Generated locally |
| Optional isolated lab observations | `docs/lab-validation.md` | Method for comparing instructor-authorized, deidentified evidence with the model | Pending optional observations |
| Instructor approval and project category | Original proposal and approval record | Instructor confirmation | Pending |
| Resolve conflicting group-size rules | Original guidelines heading and Section 1 | Instructor clarification | Pending |
| Register team and topic | Section group sheet | Instructor or section records | Pending |
| Genuine student contributions and individual commits | Contribution evidence and future repository history | Each student records their own work under their account | Unverified |
| Public repository and organized contents | Future GitHub repository | Leader verifies visibility, documentation and tracked files | Pending |
| Clean clone on another machine | Future public repository and README | Clone into an empty directory and follow README on another machine | Pending |
| Google Classroom submission | Course Classroom | Leader submits the approved public link with confirmed roster | Pending |
| Individual viva | `docs/viva-guide.md` | Students prepare their actual work and attend their individual evaluations | Pending |

## Team submission work

The group should obtain the instructor's decisions on the own idea, category and team size, then confirm registration on the section sheet. Record each student's actual contributions and meaningful commits under their own account. The leader can then verify the public repository and four academic documents, arrange an independent clean-clone check on a different machine, and submit the link on Google Classroom with the instructor-confirmed roster. The guideline dates the submission to Week 15 and calls for individual viva evaluation before the lab final.
