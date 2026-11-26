FAST — NATIONAL UNIVERSITY OF COMPUTER AND EMERGING SCIENCES
FAST School of Computing  ·  Karachi Campus  ·  Department of Artificial Intelligence & Data Science
AL-2002  Artificial Intelligence (Laboratory)  ·  Fall 2026

# Project Proposal

Semester Lab Project  ·  Weightage 1 mark

### Group Information

|  | Name | Roll Number | Section | Role in the project |
| --- | --- | --- | --- | --- |
| Leader | Muhammad Mutahir | 24K-2005 |  | Search and integration |
| Member 2 | Syed Muhammad Muzamil | 24K-2000 |  | Interface and visualization |
| Member 3 | Muhammad Abdullah | 24K-2055 |  | Model and experiments |

| Project Title | Attack-Path Analyzer and Remediation Planner |
| --- | --- |
| Project Idea | Own idea - submitted for instructor approval |
| Category | Part B - Applied / Data |
| GitHub Repository URL |  |
| Date of Submission | 21 October 2026 |

## 1.  Project Title and Summary

We propose a local application that identifies possible attack paths from an assumed compromised computer to a sensitive target in a small modeled network. It checks supplied connectivity, permissions and defined weaknesses before allowing each transition. Our BFS and Uniform Cost Search agents compare routes by steps and modeled effort. A dashboard explains the route and previews individual security fixes. The system supports cybersecurity students and analysts studying how several weaknesses combine, with results limited to the supplied model.

## 2.  Problem Statement and Motivation

A security weakness can become more serious when combined with network reachability, credentials and excessive permissions. Reviewing these relationships manually becomes difficult as alternative routes and privilege changes increase. Checking one connection at a time can miss a sequence that reaches a sensitive service. For example, an assumed compromised web server might provide a route to an internal application and then a database, but only when the required access conditions hold. Students and small teams need an understandable way to examine such scenarios and compare possible fixes. We will represent access as states and permitted transitions, then search for a target state. The shortest route by steps may differ from the route with the lowest assigned effort. An explainable, reproducible analyzer is worthwhile because it connects security reasoning with measurable AI search behavior without requiring a large training dataset.

## 3.  Problem Formulation

### 3.1  PEAS Description

| Component | Description for your project |
| --- | --- |
| Performance measure | Valid goal paths; path cost, expanded states, runtime and correct fix impact. |
| Environment | A supplied network model with access states, services, permissions and declared weaknesses. |
| Actuators | Expand valid transitions, display paths and preview changes to a copied model. |
| Sensors | JSON network records, initial access, target state and selected simulated fix. |

### 3.2  Environment and Agent Type

| Property | Classification — tick one |
| --- | --- |
| Observability | Fully observable within the supplied model |
| Determinism | Deterministic - fixed rules and costs |
| Change over time | Static during each search |
| State and actions | Discrete states and actions |
| Agents | Single-agent planner |
| Agent type | Goal-based; UCS minimizes modeled effort |

### 3.3  Problem Representation

| Element | Your representation |
| --- | --- |
| State representation | (Asset ID, privilege level); credential availability follows declared source-access rules. |
| Actions / moves | Three rules: vulnerable-service access, local privilege escalation, credential-based login. |
| Initial state | User-selected asset and assumed initial privilege. |
| Goal or terminal test | Reach the target asset with the required privilege. |
| Cost, utility, fitness or evaluation | Sum of positive action costs (1-5); BFS minimizes steps, UCS total cost. |

## 4.  Proposed AI Approach

| # | Technique | Role in the project | Own code or library |
| --- | --- | --- | --- |
| 1 | Uniform Cost Search | Minimum modeled-effort path; priority queue and best-cost map. | Own Python code |
| B | Baseline: BFS | Fewest-step valid path; queue and explored set. | Own Python code |

The modeled problem has discrete states, explicit actions and a goal test, making graph search appropriate. BFS uses a queue and an explored set to find a route with the fewest transitions. UCS uses a priority queue and best-known costs to find a minimum-cost route. Each transition receives a positive, configurable effort value from 1 to 5; these are documented assumptions rather than exploit probabilities. Both agents use the same transition rules and deterministic tie-breaking. No heuristic or trained model is required. We will implement the searches ourselves and use libraries only for the interface, plotting and independent checks. Both agents are rerun after a simulated fix to identify any remaining route.

### 4.1  Planned Class Design

AttackState: asset_id and privilege; key() gives a comparable state identifier.
NetworkEnvironment: stores validated assets/rules; successors(), goal_test(), apply_fix().
SearchAgent: base class holding the environment; defines search(start, goal).
BFSAgent: inherits SearchAgent; overrides search() using a queue.
UCSAgent: inherits SearchAgent; overrides search() using a priority queue.
The environment encapsulates rule checks; one agent interface demonstrates polymorphism.

## 5.  Scope

| # | Feature | Why it is essential |
| --- | --- | --- |
| 1 | JSON input and validation | Reject invalid input before searching. |
| 2 | BFS/UCS and search metrics | Compare path quality and search efficiency. |
| 3 | Network graph and path explanations | Make security conditions understandable. |
| 4 | Fix previews: disable weakness, revoke access, block connection | Recheck the target for any remaining route. |
| 5 | CSV, three charts and lab checks | Make results repeatable and check lab behavior. |

Out of scope

Automatic discovery, exploit execution, live monitoring, full cloud/AD policy support, optimal multi-fix scheduling, model training, paid APIs and deployment. No path in the model does not establish real-world security; unvalidated weaknesses remain simulated.

## 6.  Data or Environment Source

| Source name and URL | Team-authored JSON scenarios and generator in src/; no external dataset URL. |
| --- | --- |
| Type | Generated / simulated; selected lab observations recorded separately. |
| Access requirements | No key or paid source needed. |
| Approximate size | 26 networks: 6 checked examples plus 20 generated cases (10-30 assets); under 5 MB expected. |
| Licence / terms of use | Original synthetic data; no personal or third-party company data. |
| Offline fallback | All scenarios and generation code stored locally; no runtime network access required. |

## 7.  Evaluation Plan

| What will be compared | Own UCS implementation versus BFS on identical networks and start/goal pairs. |
| --- | --- |
| Metric(s) | Path validity, steps, total cost, states expanded and search-only runtime. |
| Baseline | BFS; independently verify expected answers on the six checked scenarios. |
| Test instances / test set | Six cases: simple path, cost trade-off, unreachable goal, cycle, blocking fix, alternate path after fix. |
| Number of runs and seed | 20 generated cases, master seed 42; 10 timing runs per agent/case. Missing paths reported explicitly. |
| Planned charts (at least three) | Three algorithm-comparison charts: states expanded, mean runtime and path cost. |

## 8.  Division of Work

| Member | Modules / components owned | Approximate share |
| --- | --- | --- |
| Muhammad Mutahir; 24K-2005 | agents.py: BFS/UCS, integration and repository coordination. | 34% |
| Syed Muhammad Muzamil; 24K-2000 | main.py / visualise.py: dashboard, graph and path explanations. | 33% |
| Muhammad Abdullah; 24K-2055 | environment.py / experiments.py: rules, scenarios, lab checks and results. | 33% |

## 9.  Milestones and Timeline

| # | Milestone — what will be demonstrably working | Target date | Owner |
| --- | --- | --- | --- |
| 1 | Validated model and six checked examples load successfully. | Build week 1 | Abdullah |
| 2 | BFS/UCS return checked paths, costs and expanded-state counts. | Build week 1 | Mutahir |
| 3 | Dashboard displays paths and all three fix previews work. | Build week 1 | Muzamil |
| 4 | 20 cases, three charts and selected container checks are reproducible. | Build week 1 | All members |
| 5 | Fresh-clone check, final documents, contribution review and viva preparation complete. | By course; Week 15 | All members |

## 10.  Expected Outcome and Risks

The outcome will be an offline dashboard that loads a network, compares BFS and UCS, explains a discovered path and previews three kinds of fixes. A repeatable runner will produce CSV results and three comparison charts. Selected connectivity and access conditions will be checked in a three-container Kali lab. Incorrect security rules are the main risk; we will use explicit preconditions and six manually checked scenarios. Dependency or container-network failures are the second risk; a pinned environment and saved JSON examples keep the analyzer usable while the lab is repaired. Results will describe modeled access, not confirmed exploitation or overall network security.

| For office use — Lab Instructor |  |
| --- | --- |
| Proposal status | Approved  ☐          Approved with changes  ☐          Revision required  ☐ |
| Comments |  |
| Signature and date |  |

End of Project Proposal
