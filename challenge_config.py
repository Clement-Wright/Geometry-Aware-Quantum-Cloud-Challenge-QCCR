"""Official challenge inputs, revision 1.

This module defines inputs only: students supply routing, Bell verification,
bootstrap analysis and protection. No cloud account or QPU access is needed.
"""

from dataclasses import dataclass

from qiskit.transpiler import CouplingMap
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error
from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2

CONFIG_VERSION = "1.0"
IBM_RUNTIME_VERSION = "0.51.0"
IBM_BACKEND_CLASS = "qiskit_ibm_runtime.fake_provider.FakeGuadalupeV2"
SYNTHETIC_BASIS_GATES = ("u", "cx")

# Common sampling settings. Report any changes in the submission.
SEED = 2026
SHOTS_PER_BASIS = 8192
BOOTSTRAP_RESAMPLES = 2000
CONFIDENCE_LEVEL = 0.95


@dataclass(frozen=True)
class SyntheticNoise:
    """Aer depolarizing strengths (not average gate infidelities)."""

    p1: float = 0.002
    p2: float = 0.02
    p_readout: float = 0.015


@dataclass(frozen=True)
class ProcessorSpec:
    name: str
    num_qubits: int
    # Directed allowed CX edges; synthetic links appear in both directions.
    edges: tuple[tuple[int, int], ...]
    ports: tuple[int, int]
    noise: SyntheticNoise | None

    def coupling_map(self):
        return CouplingMap(list(self.edges))


def _bidirectional(links):
    return tuple(sorted({edge for a, b in links for edge in ((a, b), (b, a))}))


def get_ibm_backend():
    """Load the pinned, packaged snapshot; never call backend.refresh()."""
    return FakeGuadalupeV2()


# Five-node T graph: 0--1--2--3, with 1--4. This is a pedagogical
# 2016-inspired reference, not a claimed historical device calibration.
REFERENCE_LINKS = ((0, 1), (1, 2), (2, 3), (1, 4))

# Radius-one face patch of the regular {7,3} tiling: a central heptagon
# plus its seven neighboring heptagons. Each central vertex i has radial
# neighbor 7+i. For face i, connect radial i to radial (i+1)%7 via three
# new boundary vertices 14+3*i .. 16+3*i. Every bounded face has seven
# sides; interior vertices have degree three, boundary vertices degree two.
# This is hypothetical connectivity, not a hardware/noise advantage claim.
_hyperbolic_links = []
for _i in range(7):
    _j = (_i + 1) % 7
    _hyperbolic_links.extend(((_i, _j), (_i, 7 + _i)))
    _path = (7 + _i, 14 + 3 * _i, 15 + 3 * _i, 16 + 3 * _i, 7 + _j)
    _hyperbolic_links.extend(zip(_path, _path[1:]))
HYPERBOLIC_LINKS = tuple(_hyperbolic_links)

# Keep the backend's full directed coupling map and native gates. The
# package pin freezes topology, gate errors, relaxation and readout data.
_ibm_backend = get_ibm_backend()
PROCESSORS = {
    "reference_2016": ProcessorSpec(
        "2016-inspired", 5, _bidirectional(REFERENCE_LINKS), (0, 3), SyntheticNoise()
    ),
    "ibm_today": ProcessorSpec(
        "IBM-style today", _ibm_backend.num_qubits,
        tuple(sorted(_ibm_backend.coupling_map.get_edges())), (0, 15), None
    ),
    "hyperbolic": ProcessorSpec(
        "Hyperbolic-inspired", 35, _bidirectional(HYPERBOLIC_LINKS),
        (14, 25), SyntheticNoise()
    ),
}

# Exact case order in the brief: three levels for each processor.
CASES = tuple(
    (case, processor_id, level)
    for start, processor_id in ((1, "reference_2016"), (4, "ibm_today"), (7, "hyperbolic"))
    for level, case in enumerate(range(start, start + 3), 1)
)


def make_noise_model(processor_id):
    """Level 2/3 noise; Level 1 uses the same graph/gates without noise.

    Synthetic: depolarization after every u/cx and independent symmetric
    readout flips on every measured qubit, including ancillas. No idle,
    reset, thermal or correlated errors. Compile all unitary gates to u/cx.
    IBM: packaged snapshot at temperature=0 mK, including gate errors,
    thermal relaxation and readout errors; use backend-native compilation.
    """
    spec = PROCESSORS[processor_id]
    if spec.noise is None:
        return NoiseModel.from_backend(
            get_ibm_backend(), gate_error=True, readout_error=True,
            thermal_relaxation=True, temperature=0
        )
    params = spec.noise
    model = NoiseModel(basis_gates=list(SYNTHETIC_BASIS_GATES))
    model.add_all_qubit_quantum_error(depolarizing_error(params.p1, 1), ["u"])
    model.add_all_qubit_quantum_error(depolarizing_error(params.p2, 2), ["cx"])
    p = params.p_readout
    model.add_all_qubit_readout_error(ReadoutError([[1 - p, p], [p, 1 - p]]))
    return model
