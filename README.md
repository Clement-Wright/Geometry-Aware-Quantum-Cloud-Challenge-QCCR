# Geometry-Aware Quantum Cloud Challenge

**Qiskit Fall Fest 2026 · hosted by the Quantum Student Organization at Purdue**

Route a verified Bell pair across three processor architectures, then protect it.

## The challenge in 60 seconds

On a real chip, each qubit links to only a few neighbors. Connecting distant qubits needs SWAPs (three CNOTs each), and every CNOT adds noise. So the **shape of the coupling graph** sets the cost of entangling far-apart qubits. This challenge measures that cost.

- **Task:** create $|\Phi^+\rangle = (|00\rangle + |11\rangle)/\sqrt{2}$ that *finishes* on two fixed physical qubits (**ports**) on each chip.
- **Proof:** measure in XX, YY and ZZ and compute $F = (1 + \langle XX\rangle - \langle YY\rangle + \langle ZZ\rangle)/4$. $F = 1$ is perfect; $F > 0.5$ means entangled.
- **Chips:** a 5-qubit 2016-inspired reference, a 16-qubit IBM-style fake backend, and a 35-qubit hypothetical hyperbolic-lattice chip.
- **Levels** (required):
  1. **Make it.** Ideal, noiseless Bell pair.
  2. **Break it.** Add official noise; measure the fidelity drop with error bars.
  3. **Protect it.** Add one error-detection check, discard flagged shots, and weigh the gain against the extra gates and lost shots.

Three chips × three levels = **nine cases** in one results table. A well-explained negative result is valid: you don't need to show that protection helps or that hyperbolic wins.

**Judging:** correctness and reproducibility 30% · architecture comparison 20% · protection strategy 20% · use of Qiskit 15% · evidence for your recommendation 10% · clarity 5%.

Full details are in the brief: [`Geometry-Aware Quantum Cloud Challenge.pdf`](Geometry-Aware%20Quantum%20Cloud%20Challenge.pdf).

**Optional Levels 4–5:** these are described in the brief, but the starter kit has no tooling for them. Build whatever you need yourself (noise sweeps, larger graphs, other ports, feed-forward circuits). Put this work in the notebook's "Optional extensions" section, note any inputs you changed, and keep its results out of the nine-case table.

## Schedule (Eastern Time)

| When | What |
|---|---|
| Sat, Oct 24, 8:00 PM | Hacking begins |
| **Sun, Oct 25, 4:00 PM** | **Hacking ends; submission deadline** |
| Sun, Oct 25, 4:00–5:30 PM | Presentations and judging |
| Sun, Oct 25, 6:30 PM | Results and closing |

## Start here

You'll need basic Python, quantum circuits and Bell states. Everything runs on local simulators: you don't need an IBM account or a real quantum processor (QPU).

1. Read the brief (~10 min).
2. [Set up](#setup) with uv.
3. Work through `geometry_aware_quantum_tutorial.ipynb` (~15 min). It teaches the tools on practice examples; **it does not solve the challenge.**
4. Solve Levels 1–3 in `challenge_submission.ipynb`.
5. [Submit](#submission).

| File | What it is |
|---|---|
| `Geometry-Aware Quantum Cloud Challenge.pdf` | The challenge brief |
| `geometry_aware_quantum_tutorial.ipynb` / `.html` | Qiskit toolkit (the HTML version needs no install) |
| `challenge_submission.ipynb` | Blank submission scaffold and results table |
| `challenge_config.py` | Official graphs, ports, noise and IBM backend |
| `pyproject.toml`, `uv.lock`, `.python-version` | Pinned environment; don't edit by hand |

## Setup

Everyone uses [uv](https://docs.astral.sh/uv/) so results reproduce on the judges' machines. Don't use pip or conda.

```powershell
# Install uv on Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
# Install uv on macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Open a new terminal, check that `uv --version` works, then fork this repo and clone your fork:

```bash
git clone https://github.com/<your-username>/<your-fork>.git
```

Inside the fork, `uv sync` installs Python 3.12, Qiskit 2.4.1, Aer 0.17.2 and IBM Runtime 0.51.0:

```bash
uv sync
```

```bash
uv run jupyter lab geometry_aware_quantum_tutorial.ipynb
```

Always launch with `uv run ...`. In VS Code, choose **Select Kernel → Python Environments → `.venv`**.

**Adding a package:** use `uv add <package-name>` and commit `pyproject.toml` and `uv.lock`. Don't upgrade `qiskit`, `qiskit-aer` or `qiskit-ibm-runtime`; those pins define the benchmark.

## Official inputs

[`challenge_config.py`](challenge_config.py) (revision 1.0) is the spec every team uses. Import `PROCESSORS`, `CASES`, `get_ibm_backend` and `make_noise_model`. Each spec has `num_qubits`, directed `edges`, `ports`, `noise` and `coupling_map()`.

| Processor ID | Graph | Ports | Level 2/3 noise |
|---|---|---|---|
| `reference_2016` | 5-qubit T graph | `(0, 3)` | Synthetic depolarizing + readout |
| `ibm_today` | 16-qubit Guadalupe snapshot | `(0, 15)` | Bundled backend calibration |
| `hyperbolic` | 35-qubit, eight-heptagon {7,3} patch | `(14, 25)` | Synthetic depolarizing + readout |

- **Synthetic noise:** Aer depolarizing `p1=0.002` after every `u` and `p2=0.02` after every `cx` (not average gate infidelities), plus readout flip `0.015` on every measured qubit, ancillas included. Compile to `u`/`cx`, or gates will miss the noise. There are no idle, reset, relaxation or correlated errors.
- **IBM noise:** `FakeGuadalupeV2` from the pinned `qiskit-ibm-runtime==0.51.0`, at 0 mK, using its full coupling map and native gates via `AerSimulator.from_backend(get_ibm_backend())` or `make_noise_model("ibm_today")`. Never refresh it or swap backends. It's a historical baseline, not a claim about current hardware ([docs](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/fake-provider-fake-guadalupe-v2)).
- **Levels:** Level 1 uses the same graph and basis gates with noise off. Levels 2–3 use official noise, including on protection gates and ancilla readout. Don't add delays or resets to the core benchmark.
- **Sampling:** 8,192 shots per basis, 2,000 bootstrap resamples, 95% intervals, base seed 2026. Derive a distinct seed per case/basis and record every seed. Use a memory-efficient Aer method (e.g. `matrix_product_state`) for the 35-qubit graph.
- **Your choices:** layout, routing, optimization and protection.
- **Caveats:** neither synthetic model is a real calibration. The graphs differ in size and port distance, and IBM noise differs from synthetic noise, so don't attribute every difference to geometry.

## Reporting conventions

These rules keep the nine-case table comparable across teams:

- **Reference circuit:** costs are for the full **ZZ circuit** (preparation, routing, protection, ancilla readout and port measurements). Report XX and YY costs separately. Noisy baselines reuse the ideal compiled circuit.
- **Depth:** native-gate depth **including measurements**, with barriers removed; don't remove any gates.
- **Two-qubit gates:** all of them in the native circuit after SWAP decomposition, protection and ancilla routing included.
- **SWAPs:** explicit SWAPs in the routed circuit just before native decomposition. Keep that circuit or record the pass count; don't estimate SWAPs as CNOTs ÷ 3.
- **Physical qubits:** distinct qubits touched by non-barrier operations, including ancillas and routing qubits, not the backend width.
- **Fidelity:** F from all three bases with a 95% bootstrap interval. For Level 3, apply the same protection and acceptance rule before the basis rotations in every basis, and never select shots on the final port outcomes.
- **Yield:** total accepted ÷ attempted shots across all three bases, plus total discarded, and per-basis attempted/accepted/discarded counts. Without postselection, yield = 1 and discarded = 0.

## Submission

**Deadline: Sunday, Oct 25, 4:00 PM ET.** Open a pull request from your fork to the [main challenge repository](https://github.com/sjothiba28/Geometry-Aware-Quantum-Cloud-Challenge-MASTER).

1. Complete `challenge_submission.ipynb`. Cases 1–3 are the 2016 model, 4–6 IBM and 7–9 hyperbolic; each group runs ideal, noisy, protected.
2. Include the three coupling graphs with labeled ports, the transpiled circuits, and the full results table (fidelity with CI, depth, two-qubit gates, SWAPs, physical qubits, yield and discarded shots).
3. Record versions, shots, seeds, bootstrap settings, and layout/routing/optimization settings. Explain how you verified the ports and counted costs.
4. Discuss the architecture comparison, the cost and benefit of protection, the limits of your conclusions, and one evidence-backed recommendation for future cloud systems.
5. Restart the kernel, run all cells and save the outputs. Commit the notebook (plus `pyproject.toml`/`uv.lock` if changed). Leave `challenge_config.py` unchanged.
6. Push to a branch and open a PR against the main repo's default branch, titled `Submission: <team name>`. List team members, the notebook path, the results commit hash and any extra steps.

Judges will clone your branch, run `uv sync`, and run:

```bash
uv run jupyter lab challenge_submission.ipynb
```

## Troubleshooting

- **`uv` not recognized:** reopen the terminal (or VS Code) after installing.
- **Can't find `qiskit`:** the kernel isn't `.venv`. Use `uv run jupyter lab` or pick `.venv` in VS Code.
- **Environment broken:** delete `.venv` and run `uv sync`.
