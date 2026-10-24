# Geometry-Aware Quantum Cloud Challenge

**Qiskit Fall Fest 2026 · hosted by the Quantum Student Organization at Purdue**

Route a verified Bell pair across three processor architectures, then protect it.

## The challenge in 60 seconds

On a real quantum chip, each qubit is linked to only a few neighbors. To make two distant qubits interact, the compiler inserts SWAP gates. Each SWAP costs three CNOTs, and every CNOT adds noise. So the **shape of the chip's coupling graph** decides how expensive it is to entangle two far-apart qubits. This challenge measures that cost.

- **The task:** create the Bell state $|\Phi^+\rangle = (|00\rangle + |11\rangle)/\sqrt{2}$ between two **ports**, a fixed pair of physical qubits on each chip. The pair must *finish* on those two qubits, so the distance between the ports sets the routing cost.
- **How you prove it worked:** measure the pair in the XX, YY and ZZ bases and combine the three correlators into the Bell fidelity $F = (1 + \langle XX\rangle - \langle YY\rangle + \langle ZZ\rangle)/4$. A perfect pair gives $F = 1$; $F > 0.5$ means the qubits are entangled.
- **The three chips:** a 5-qubit 2016-inspired reference, a 16-qubit IBM-style processor (a fake backend), and a 35-qubit hypothetical chip built from a hyperbolic lattice.
- **The three levels** (required for every team):
  1. **Make it.** An ideal, noiseless Bell pair on each chip.
  2. **Break it.** Add each chip's official noise and measure how much fidelity drops, with error bars.
  3. **Protect it.** Add one error-detection check, discard flagged shots, and report whether the gain was worth the extra gates and lost shots.

Three chips × three levels = **nine cases**, which fill one results table. Levels 4–5 in the brief are optional extensions.

**What counts as success:** complete all nine cases, verify the final ports, and explain the measured routing and protection tradeoffs with reproducible evidence. A valid submission does not need to show that protection improves fidelity or that hyperbolic connectivity wins. A carefully explained negative result is useful.

**How you're judged:** scientific correctness and reproducibility 30% · architecture comparison 20% · protection strategy 20% · effective use of Qiskit 15% · evidence for your future-system recommendation 10% · clarity 5%.

The full brief, with diagrams and per-level details, is [`Geometry-Aware Quantum Cloud Challenge.pdf`](Geometry-Aware%20Quantum%20Cloud%20Challenge.pdf).

## Schedule

**Event dates:** October 24–25, 2026 · **Timezone:** Eastern Time (ET). All times below are ET.

| When | What |
|---|---|
| Saturday, Oct 24, 8:00 PM | Hacking begins |
| **Sunday, Oct 25, 4:00 PM** | **Hacking ends. Submit your work by this time.** |
| Sunday, Oct 25, 4:00–5:30 PM | Presentations and judging |
| Sunday, Oct 25, 6:30 PM | Results and closing remarks |

## Start here

**Expected background:** basic Python, quantum circuits, Bell states and measurements. The tutorial introduces the Qiskit tools used in the challenge.

**Run locally:** all required cases use simulators on your computer. You do not need an IBM account, API key or access to a real quantum processor. Internet access is needed to install the environment.

1. **Read the brief** (the PDF), about 10 minutes.
2. **Set up the environment** with uv ([Setup](#setup-use-uv) below).
3. **Work through the tutorial**, `geometry_aware_quantum_tutorial.ipynb`, about 15 minutes. It teaches each tool you need on practice examples. **It does not solve the challenge.**
4. **Solve Levels 1–3** in `challenge_submission.ipynb`, using the official inputs from `challenge_config.py`.
5. **Submit** following the [submission instructions](#submission-instructions).

## What's in this repo

| File | What it is |
|---|---|
| `Geometry-Aware Quantum Cloud Challenge.pdf` | The challenge brief: levels, what to report, judging |
| `geometry_aware_quantum_tutorial.ipynb` | A short Qiskit toolkit (about 15 minutes). Read it first. |
| `geometry_aware_quantum_tutorial.html` | The same tutorial, viewable in a browser without installing anything |
| `challenge_submission.ipynb` | Blank Levels 1–3 submission scaffold and nine-case results table |
| `challenge_config.py` | Official processor graphs, ports, noise and fixed IBM backend |
| `pyproject.toml`, `uv.lock`, `.python-version` | The exact environment everyone uses. Don't edit these by hand. |

## Setup (use uv)

Everyone uses [uv](https://docs.astral.sh/uv/), so every team runs the same Python and the same package versions. Your results then reproduce on the judges' machines. Don't use `pip install` or conda for this project.

**1. Install uv** (once per computer):

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Open a new terminal afterwards and check that `uv --version` works.

**2. Fork this repo on GitHub, then clone your fork:**

```bash
git clone https://github.com/<your-username>/<your-fork>.git
cd <your-fork>
```

**3. Create the environment.** This installs Python 3.12 if you don't have it, plus Qiskit 2.4.1, Aer 0.17.2 and IBM Runtime 0.51.0:

```bash
uv sync
```

**4. Open the tutorial:**

```bash
uv run jupyter lab geometry_aware_quantum_tutorial.ipynb
```

Always start things with `uv run ...`, which runs them inside the project environment without activating it.

**Using VS Code instead?** Run `uv sync`, open the notebook, then click **Select Kernel → Python Environments** and choose the `.venv` in this folder.

## Official challenge inputs (reference)

You'll come back to this section while you work. It's the exact specification every team uses.

- [`challenge_config.py`](challenge_config.py) is the official specification (revision 1.0): all graph edges, fixed physical ports, noise parameters, backend and common sampling settings. These definitions supply the starter kit referenced by the brief.
- [`challenge_submission.ipynb`](challenge_submission.ipynb) is the blank student scaffold for Levels 1–3, with the nine-case results table. Write your own solution code.

| Processor ID | Graph | Fixed ports | Level 2/3 noise |
|---|---|---|---|
| `reference_2016` | Five-qubit T graph | `(0, 3)` | Synthetic depolarizing + readout |
| `ibm_today` | Full 16-qubit Guadalupe snapshot | `(0, 15)` | Bundled backend calibration |
| `hyperbolic` | 35-qubit, eight-heptagon patch of the {7,3} tiling | `(14, 25)` | Synthetic depolarizing + readout |

Both synthetic models use Aer depolarizing strengths `p1=0.002` after every `u` and `p2=0.02` after every `cx`, plus symmetric readout flip probability `0.015` on every measured qubit, including ancillas. These strengths are not average gate infidelities. Compile to `u`/`cx`; unrecognized gates would miss this noise. Synthetic models have no idle, reset, relaxation or correlated errors.

The exact IBM backend is `qiskit_ibm_runtime.fake_provider.FakeGuadalupeV2` from **`qiskit-ibm-runtime==0.51.0`**, pinned in the environment and lockfile. Use its full coupling map, native gates and packaged calibration, at 0 mK with `AerSimulator.from_backend(get_ibm_backend())` or `make_noise_model("ibm_today")`. Do not refresh its calibration or substitute another backend. Guadalupe is a historical snapshot used here as the IBM-style connectivity and compilation baseline, not a claim about current hardware performance. No IBM account is needed. See the [IBM fake-backend documentation](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/fake-provider-fake-guadalupe-v2) for background; the pinned package in this repo determines the inputs.

Import `PROCESSORS`, `CASES`, `get_ibm_backend` and `make_noise_model` from the config. Each processor spec exposes `num_qubits`, directed `edges`, `ports`, `noise`, and `coupling_map()`. Level 1 uses the same topology and compilation basis as its noisy baseline, with noise disabled. Levels 2 and 3 use the official noise, including errors on protection gates and ancilla readout. Do not add delays or resets to the core benchmark: synthetic models do not characterize their errors.

Defaults are 8,192 shots per basis, 2,000 bootstrap resamples and 95% intervals, with base seed 2026. Derive distinct simulator seeds for each case/basis; record all seeds and any sampling changes. Layout, routing, optimization and protection are student choices. Use a memory-efficient Aer method such as `matrix_product_state` for the 35-qubit graph; a full density matrix is impractical. Count physical qubits actually touched rather than the full backend width.

The five-qubit model is a pedagogical reference. The hyperbolic graph is hypothetical connectivity; its eight bounded faces are heptagons, with degree-three interior vertices and degree-two boundary vertices. Neither model is a measured hardware calibration. The graphs differ in size and port distance, and IBM noise differs from synthetic noise; explain these effects separately rather than attributing every difference to geometry.

Use the same official inputs for all teams. Keep alternative graphs, ports, noise models and optional extensions separate from the common benchmark.

## Common reporting conventions

Use these conventions for the official nine-case table so every team reports comparable costs:

- **Reference circuit:** report costs for the complete **ZZ measurement circuit** for each case, including preparation, routing, protection (Level 3), ancilla readout and final port measurements. Supply XX and YY circuit costs separately; their basis rotations are included in those supplementary costs. Each noisy baseline uses the same compiled circuit as its ideal counterpart.
- **Depth:** report the native-gate compiled circuit depth **including measurements**, with barriers removed for the depth calculation. Do not remove gates or measurements when calculating costs.
- **Two-qubit gates:** count all two-qubit gates in that native-gate circuit after SWAP decomposition; exclude barriers. Count the gates used for protection and ancilla routing too.
- **SWAPs:** count explicit SWAPs in the routed version of that same circuit immediately before native-gate decomposition. Preserve that intermediate circuit or record the routing pass count. Do not estimate SWAPs by dividing the final CNOT count by three or by routing a separate circuit with different settings.
- **Physical qubits:** count distinct physical qubits touched by non-barrier operations in the compiled circuit, including ancillas and routing qubits. Do not report the full backend width unless all those qubits are actually used.
- **Fidelity and uncertainty:** use all three bases to report F and its 95% bootstrap interval. For Level 3, use accepted shots and the same protection procedure and acceptance rule before the basis rotations for all three measurements; do not select shots by the final port outcomes.
- **Yield and discarded shots:** in the main table, yield is total accepted shots across XX, YY and ZZ divided by total attempted shots across those bases; discarded shots is the total discarded across the three bases. Also report attempted, accepted and discarded counts separately for each basis. Without postselection, yield is 1 and discarded shots is 0.

## Submission instructions

**Deadline: Sunday, October 25, 2026, 4:00 PM ET**, when hacking ends.

**Submit by opening a pull request from your fork to the [main challenge repository](https://github.com/sjothiba28/Geometry-Aware-Quantum-Cloud-Challenge-MASTER). Organizers will review your pull request.**

1. Complete `challenge_submission.ipynb` in your fork. Cases 1–3 cover the 2016-inspired model, 4–6 the IBM-style model, and 7–9 the hyperbolic-inspired model; within each group the levels are ideal, noisy and protected.
2. Include all three coupling graphs with labeled ports, the transpiled circuits, and the completed nine-case results table. Report fidelity with a 95% confidence interval, depth, two-qubit gates, SWAPs, physical qubits including ancillas, acceptance fraction and discarded shots. For protection, report conditional fidelity and per-basis acceptance statistics.
3. Record assumptions, package versions, shots per basis, simulator/transpiler seeds, bootstrap settings, layout, routing and optimization settings. Explain how you verified that the pair finishes on the fixed physical ports and how you count circuit costs.
4. Explain the architecture comparison, the cost and benefit of protection, the limits of your conclusions, and one evidence-backed hardware or software recommendation for future cloud systems.
5. Restart the kernel, run all cells from top to bottom and save the outputs. Commit the notebook and supporting files; include `pyproject.toml` and `uv.lock` if you added dependencies. Keep the official config unchanged.
6. Push your completed work to a branch in your fork, then open a pull request to the [main challenge repository](https://github.com/sjothiba28/Geometry-Aware-Quantum-Cloud-Challenge-MASTER) by **Sunday 4:00 PM**. Choose the main repository's default branch as the base and your submission branch as the head. Title it `Submission: <team name>`. In the description, include team members, the notebook path, the commit hash used for your results, and any extra reproduction steps. Leave the pull request open for organizer review.

Judges should be able to clone your submission branch, run `uv sync`, and open the completed notebook with:

```bash
uv run jupyter lab challenge_submission.ipynb
```

## Adding a package

If your team needs another library, add it with uv so it is recorded in `pyproject.toml` and `uv.lock`:

```bash
uv add <package-name>
```

Commit both files. Whoever runs your notebook then gets the same versions with one `uv sync`. Don't upgrade `qiskit`, `qiskit-aer` or `qiskit-ibm-runtime`: these pins define the benchmark environment and backend snapshot.

## Troubleshooting

- **`uv` is not recognized:** close and reopen the terminal after installing, or restart VS Code.
- **The notebook can't find `qiskit`:** the kernel isn't the project's `.venv`. Start Jupyter with `uv run jupyter lab`, or select `.venv` as the kernel in VS Code.
- **Something is broken after experimenting:** delete the `.venv` folder and run `uv sync` again.
