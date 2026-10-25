"""Optional Bell transport and cycle-storage studies, separate from Cases 1-9."""

from collections import Counter
from functools import reduce

import networkx as nx
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.classical import expr
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import SabreSwap
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error, pauli_error

from challenge_config import (
    BOOTSTRAP_RESAMPLES, CONFIDENCE_LEVEL, PROCESSORS, SHOTS_PER_BASIS,
    get_ibm_backend,
)
from simulation_seeds import aer_seed

BASES = ("XX", "YY", "ZZ")
SABRE_TRIALS = 4


def add_readout(circuit, ports, basis):
    """Rotate the requested Pauli observable onto the measured Z axis."""
    if basis not in BASES:
        raise ValueError(f"Unsupported basis: {basis}")
    for port in ports:
        if basis == "YY":
            circuit.sdg(port)
        if basis in ("XX", "YY"):
            circuit.h(port)
    circuit.measure(list(ports), [0, 1])


def ghz_transport(model_id, route, basis, *, growth="balanced", mode="feedforward"):
    """Connect the fixed ports by measuring the interior of a routed GHZ state."""
    model = PROCESSORS[model_id]
    route = list(route)
    graph = nx.Graph(model.edges)
    if (len(route) < 2 or len(set(route)) != len(route)
            or (route[0], route[-1]) != model.ports
            or not all(graph.has_edge(a, b) for a, b in zip(route, route[1:]))):
        raise ValueError("Supply a simple physical path between the fixed ports")
    if growth not in ("left", "balanced"):
        raise ValueError("Growth must be left or balanced")
    if mode not in ("feedforward", "select_even", "uncorrected"):
        raise ValueError("Choose feedforward, select_even, or uncorrected")
    circuit = QuantumCircuit(model.num_qubits, len(route),
                             name=f"ghz_{growth}_{mode}_{basis}")
    d = len(route) - 1
    k = 0 if growth == "left" else (d - 1) // 2
    circuit.h(route[k])
    circuit.cx(route[k], route[k + 1])
    # Each CNOT copies a computational-basis label into a fresh zero.
    # The resulting GHZ state keeps the relative phase in a joint amplitude.
    for j in range(k, 0, -1):
        circuit.cx(route[j], route[j - 1])
    for j in range(k + 1, d):
        circuit.cx(route[j], route[j + 1])
    for i, qubit in enumerate(route[1:-1], start=2):
        circuit.h(qubit)
        circuit.measure(qubit, i)
    if mode == "feedforward" and d > 1:
        # X-readout outcomes multiply the Bell phase by (-1)**parity.
        # One physical Z removes an odd phase before the port basis rotations.
        parity = reduce(expr.bit_xor, (expr.lift(circuit.clbits[i])
                                      for i in range(2, len(route))))
        with circuit.if_test(parity):
            circuit.z(route[0])
    circuit.barrier(*route)
    add_readout(circuit, model.ports, basis)
    return circuit


def bell_link_transport(model_id, route, basis):
    """Fuse neighboring Bell links with Bell measurements and physical X/Z corrections."""
    model = PROCESSORS[model_id]
    route = list(route)
    graph = nx.Graph(model.edges)
    if (len(route) < 2 or len(set(route)) != len(route)
            or (route[0], route[-1]) != model.ports
            or not all(graph.has_edge(a, b) for a, b in zip(route, route[1:]))):
        raise ValueError("Supply a simple path between the fixed physical ports")
    circuit = QuantumCircuit(model.num_qubits, len(route), name=f"bell_links_{basis}")
    even_size = 2 * (len(route) // 2)
    for i in range(0, even_size, 2):
        circuit.h(route[i])
        circuit.cx(route[i], route[i + 1])
    phase_bits, flip_bits = [], []
    for i in range(1, even_size - 1, 2):
        # A Bell measurement joins the two links meeting at these vertices.
        # Its X outcome supplies a phase bit; its Z outcome supplies a flip bit.
        circuit.cx(route[i], route[i + 1])
        circuit.h(route[i])
        circuit.measure(route[i], i + 1)
        circuit.measure(route[i + 1], i + 2)
        phase_bits.append(i + 1)
        flip_bits.append(i + 2)
    if len(route) % 2:
        # With an odd number of vertices, one-bit teleportation carries the
        # last Bell half across the remaining edge into a fresh zero.
        i = len(route) - 2
        circuit.cx(route[i], route[i + 1])
        circuit.h(route[i])
        circuit.measure(route[i], i + 1)
        phase_bits.append(i + 1)
    for indices, correction, port in ((phase_bits, "z", route[0]),
                                       (flip_bits, "x", route[-1])):
        if indices:
            parity = reduce(expr.bit_xor, (expr.lift(circuit.clbits[i]) for i in indices))
            with circuit.if_test(parity):
                getattr(circuit, correction)(port)
    circuit.barrier(*route)
    add_readout(circuit, model.ports, basis)
    return circuit


def sabre_transport(model_id, basis, *, seed):
    """Route a remote Bell CNOT with SABRE, then restore its output permutation."""
    model = PROCESSORS[model_id]
    logical = QuantumCircuit(model.num_qubits)
    logical.h(model.ports[0])
    logical.cx(*model.ports)
    # Full-width q[i] already denotes physical vertex i. Fix the trial count
    # as well as the seed so routing results reproduce across CPU counts.
    routed = PassManager(SabreSwap(model.coupling_map(), heuristic="decay", seed=seed,
                                   trials=SABRE_TRIALS)).run(logical)
    circuit = QuantumCircuit(model.num_qubits, 2, name=f"sabre_restored_{basis}")
    circuit.compose(routed, inplace=True)
    # SABRE's SWAP product describes its output permutation. Reversing that
    # product places the logical outputs back on the required physical ports.
    for inst in reversed(routed.data):
        if inst.operation.name == "swap":
            circuit.swap(*(routed.find_bit(q).index for q in inst.qubits))
    circuit.barrier(*model.ports)
    add_readout(circuit, model.ports, basis)
    return circuit


def two_stabilizer_check(model_id, preparation, parity_check, basis, *, fault=None):
    """Measure ZZ then XX, transporting the measured meter back between checks."""
    model = PROCESSORS[model_id]
    unitary = QuantumCircuit(model.num_qubits)
    meter = None
    for inst in parity_check.data:
        qs = [parity_check.find_bit(q).index for q in inst.qubits]
        if inst.operation.name == "measure":
            meter = qs[0]
        else:
            unitary.append(inst.operation, qs)
    if meter is None:
        raise ValueError("The supplied check must measure its final meter")
    circuit = QuantumCircuit(model.num_qubits, 4, name=f"ZZ_XX_check_{basis}")
    circuit.compose(preparation, inplace=True)
    if fault is not None:
        if fault not in ("X", "Y", "Z"):
            raise ValueError("Control fault must be X, Y, or Z")
        getattr(circuit, fault.lower())(model.ports[0])
    circuit.compose(unitary, inplace=True)
    circuit.measure(meter, 2)
    # Reverse the routing permutation to return the measured meter to its
    # starting vertex. Its physical ZZ value becomes the next check's offset.
    for inst in reversed(unitary.data):
        if inst.operation.name == "swap":
            circuit.swap(*(unitary.find_bit(q).index for q in inst.qubits))
    for port in model.ports:
        circuit.h(port)
    circuit.compose(unitary, inplace=True)
    circuit.measure(meter, 3)
    # H Z H = X, so the second extraction measures XX in the original basis.
    # Requiring c2=c3=0 selects both positive stabilizers with an ideal meter.
    for port in model.ports:
        circuit.h(port)
    circuit.barrier(*model.ports)
    add_readout(circuit, model.ports, basis)
    return circuit


def compile_optional(circuit, model_id, *, seed):
    """Keep the physical assignment while translating gates to the native basis."""
    model = PROCESSORS[model_id]
    basis = (list(get_ibm_backend().operation_names) if model_id == "ibm_today"
             else ["u", "cx", "id"])
    # A generic gate-basis target lets Aer execute the classical if block.
    # IBM gate channels still attach by native instruction and physical qubits.
    return transpile(circuit, coupling_map=model.coupling_map(), basis_gates=basis,
                     initial_layout=list(range(model.num_qubits)), routing_method="none",
                     optimization_level=0, seed_transpiler=seed)


def _instructions(circuit, qmap=None, cmap=None):
    """Visit native gates inside each true control-flow branch with global indices."""
    qmap = list(range(circuit.num_qubits)) if qmap is None else qmap
    cmap = list(range(circuit.num_clbits)) if cmap is None else cmap
    for inst in circuit.data:
        qs = [qmap[circuit.find_bit(q).index] for q in inst.qubits]
        cs = [cmap[circuit.find_bit(c).index] for c in inst.clbits]
        if inst.operation.name == "if_else":
            yield inst.operation, qs, cs
            yield from _instructions(inst.operation.blocks[0], qs, cs)
        else:
            yield inst.operation, qs, cs


def verify_native(circuit, model_id, ports):
    """Check directed native edges and the two designated output bits."""
    allowed = set(PROCESSORS[model_id].edges)
    native_names = (set(get_ibm_backend().operation_names) if model_id == "ibm_today"
                    else {"u", "cx", "id", "measure"})
    measured = {}
    for op, qs, cs in _instructions(circuit):
        if op.name in ("barrier", "if_else"):
            continue
        if op.name not in native_names:
            raise AssertionError(f"Unexpected native instruction {op.name}")
        if len(qs) == 2 and tuple(qs) not in allowed:
            raise AssertionError(f"Illegal physical edge {qs}")
        if op.name == "measure" and cs[0] < 2:
            measured[cs[0]] = qs[0]
    if measured != dict(enumerate(ports)):
        raise AssertionError(f"Output ports moved: {measured}")


def resource_costs(native, source):
    """Count full ZZ resources and the dependency depth with the Z branch taken."""
    counts, touched = Counter(), set()
    for op, qs, _ in _instructions(native):
        if op.name == "barrier":
            continue
        counts[op.name] += 1
        if op.name != "if_else":
            touched.update(qs)
            if len(qs) == 2:
                counts["two_qubit"] += 1

    qready = [0] * native.num_qubits
    cready = [0] * native.num_clbits

    def schedule(circuit, qmap, cmap):
        for inst in circuit.data:
            op = inst.operation
            qs = [qmap[circuit.find_bit(q).index] for q in inst.qubits]
            cs = [cmap[circuit.find_bit(c).index] for c in inst.clbits]
            if op.name == "barrier":
                # The fence has zero gate duration and synchronizes its wires.
                # In particular, all data reach the storage boundary together.
                start = max((qready[q] for q in qs), default=0)
                for q in qs:
                    qready[q] = start
                continue
            start = max([qready[q] for q in qs] + [cready[c] for c in cs], default=0)
            if op.name == "if_else":
                # The correction waits for every syndrome bit used by its condition.
                # Scheduling the true block gives the maximum executed gate depth.
                for q in qs:
                    qready[q] = start
                schedule(op.blocks[0], qs, cs)
            else:
                for q in qs:
                    qready[q] = start + 1
                if op.name == "measure":
                    for c in cs:
                        cready[c] = start + 1

    schedule(native, list(range(native.num_qubits)), list(range(native.num_clbits)))
    return {
        "Depth max": max(qready + cready, default=0),
        "Two-qubit gates": counts["two_qubit"],
        "SWAPs": sum(op.name == "swap" for op, _, _ in _instructions(source)),
        "Physical qubits": len(touched), "Measurements": counts["measure"],
        "Conditional operations": counts["if_else"], "u gates max": counts["u"],
        "Storage markers": counts["id"],
    }


def count_statistics(counts_by_basis, acceptance, *, seed,
                     resamples=BOOTSTRAP_RESAMPLES, confidence=CONFIDENCE_LEVEL):
    """Select using syndrome bits, then estimate the two-port Bell fidelity."""
    if acceptance not in ("all", "even", "zero"):
        raise ValueError("Acceptance must be all, even, or zero")
    accepted, accounting, correlations = {}, [], {}
    for basis in BASES:
        marginal = Counter()
        attempted = sum(counts_by_basis[basis].values())
        for key, count in counts_by_basis[basis].items():
            bits = key.replace(" ", "")[::-1]
            syndrome = bits[2:]
            keep = (acceptance == "all"
                    or acceptance == "even" and sum(map(int, syndrome)) % 2 == 0
                    or acceptance == "zero" and all(bit == "0" for bit in syndrome))
            if keep:
                marginal[bits[:2][::-1]] += int(count)
        accepted[basis] = dict(marginal)
        n = sum(marginal.values())
        correlations[basis] = (sum((1 if key[0] == key[1] else -1) * value
                                  for key, value in marginal.items()) / n if n else None)
        accounting.append({"Basis": basis, "Attempted": attempted, "Accepted": n,
                           "Discarded": attempted - n})
    total = sum(row["Attempted"] for row in accounting)
    kept = sum(row["Accepted"] for row in accounting)
    fidelity, interval = None, (None, None)
    if all(value is not None for value in correlations.values()):
        fidelity = (1 + correlations["XX"] - correlations["YY"] + correlations["ZZ"]) / 4
        rng = np.random.default_rng(seed)
        draws = {}
        for basis in BASES:
            n = sum(accepted[basis].values())
            p_even = sum(v for k, v in accepted[basis].items() if k[0] == k[1]) / n
            # Port parity is a binary statistic. Binomial resampling equals
            # multinomial resampling followed by the same parity marginal.
            draws[basis] = 2 * rng.binomial(n, p_even, size=resamples) / n - 1
        fdraws = (1 + draws["XX"] - draws["YY"] + draws["ZZ"]) / 4
        alpha = (1 - confidence) / 2
        interval = tuple(float(x) for x in np.quantile(fdraws, [alpha, 1 - alpha]))
    return {"F": fidelity, "95% CI": interval, "Yield": kept / total if total else 0.0,
            "Discarded shots": total - kept, "accepted_counts": accepted,
            "correlations": correlations, "shot_accounting": accounting}


def cycle_layout():
    """Choose a canonical seven-cycle and an external reference next to its root."""
    graph = nx.Graph(PROCESSORS["hyperbolic"].edges)
    cycles = []
    for cycle in nx.cycle_basis(graph):
        i = cycle.index(min(cycle))
        forward = cycle[i:] + cycle[:i]
        backward = [forward[0]] + list(reversed(forward[1:]))
        cycles.append(min(forward, backward))
    for cycle in sorted(cycles, key=lambda c: (len(c), c)):
        neighbors = sorted(set(graph.neighbors(cycle[0])) - set(cycle))
        if neighbors:
            return cycle, neighbors[0]
    raise ValueError("A cycle with an external reference neighbor is required")


def cycle_memory_circuit(data, reference, basis, *, close_cycle=False, faults=None):
    """Encode, check local ZZ stabilizers, and decode one half of a Bell pair."""
    data = list(data)
    graph = nx.Graph(PROCESSORS["hyperbolic"].edges)
    if not data or len(set(data)) != len(data) or reference in data:
        raise ValueError("Use distinct data vertices and an external reference")
    links = list(zip(data, data[1:]))
    if not graph.has_edge(reference, data[0]) or not all(graph.has_edge(*e) for e in links):
        raise ValueError("The encoding must follow physical edges")
    if close_cycle:
        if len(data) < 3 or not graph.has_edge(data[-1], data[0]):
            raise ValueError("The closing stabilizer needs a physical cycle edge")
        checks = links + [(data[-1], data[0])]
    else:
        checks = links
    circuit = QuantumCircuit(PROCESSORS["hyperbolic"].num_qubits, 2 + len(checks),
                             name=f"memory_n{len(data)}_{'cycle' if close_cycle else 'path'}_{basis}")
    circuit.h(reference)
    circuit.cx(reference, data[0])
    for a, b in links:
        circuit.cx(a, b)
    circuit.barrier(reference, *data)
    for q in data:
        # An id marks one storage interval. Its optional Pauli channel applies
        # once to each data qubit while the reference has no storage channel.
        circuit.id(q)
    for q, pauli in (faults or {}).items():
        if q not in data or pauli not in ("X", "Y", "Z"):
            raise ValueError("Control faults must be X, Y, or Z on a data qubit")
        getattr(circuit, pauli.lower())(q)
    circuit.barrier(reference, *data)
    for i, (a, b) in enumerate(checks, start=2):
        # CNOT maps Z_b to Z_a Z_b. Measuring b reads that parity; the
        # second CNOT restores the data representation within its eigenspace.
        circuit.cx(a, b)
        circuit.measure(b, i)
        circuit.cx(a, b)
    for a, b in reversed(links):
        circuit.cx(a, b)
    circuit.barrier(reference, *data)
    add_readout(circuit, (reference, data[0]), basis)
    return circuit


def storage_noise(gate_scale, p_x, p_z=0.0, *, clifford=False):
    """Independent storage X/Z faults plus scaled synthetic operation noise."""
    if gate_scale < 0 or not (0 <= p_x <= 1 and 0 <= p_z <= 1):
        raise ValueError("Supply a nonnegative gate scale and probabilities in [0,1]")
    params = PROCESSORS["hyperbolic"].noise
    p1, p2, readout = params.p1 * gate_scale, params.p2 * gate_scale, params.p_readout * gate_scale
    if p1 > 1 or p2 > 1 or readout > 0.5:
        raise ValueError("The operation-noise sweep exceeds its probability bounds")
    singles = ["h", "s", "sdg", "x", "y", "z"] if clifford else ["u"]
    model = NoiseModel(basis_gates=singles + ["cx", "id"])
    if p1:
        model.add_all_qubit_quantum_error(depolarizing_error(p1, 1), singles)
    if p2:
        model.add_all_qubit_quantum_error(depolarizing_error(p2, 2), ["cx"])
    if readout:
        model.add_all_qubit_readout_error(ReadoutError([[1 - readout, readout],
                                                       [readout, 1 - readout]]))
    if p_x or p_z:
        model.add_all_qubit_quantum_error(pauli_error([
            ("I", (1 - p_x) * (1 - p_z)), ("X", p_x * (1 - p_z)),
            ("Z", (1 - p_x) * p_z), ("Y", p_x * p_z),
        ]), ["id"])
    return model


def ideal_storage_prediction(n, p_x, p_z=0.0):
    """Exact Bell fidelity and yield with ideal encoding/checks/decoding/readout."""
    accepted = (1 - p_x) ** n + p_x ** n
    phase_even = (1 + (1 - 2 * p_z) ** n) / 2
    return {"Yield": accepted, "F": (1 - p_x) ** n * phase_even / accepted
            if accepted else None}


def fidelity_gain(protected, baseline, *, seed, resamples=BOOTSTRAP_RESAMPLES):
    """Bootstrap the difference between two independent accepted samples."""
    if protected["F"] is None or baseline["F"] is None:
        return {"Gain": None, "95% CI": (None, None)}
    rng = np.random.default_rng(seed)

    def draw(result):
        correlations = {}
        for basis in BASES:
            counts = result["accepted_counts"][basis]
            n = sum(counts.values())
            even = sum(v for k, v in counts.items() if k[0] == k[1])
            correlations[basis] = 2 * rng.binomial(n, even / n, size=resamples) / n - 1
        return (1 + correlations["XX"] - correlations["YY"] + correlations["ZZ"]) / 4

    differences = draw(protected) - draw(baseline)
    alpha = (1 - CONFIDENCE_LEVEL) / 2
    interval = tuple(float(x) for x in np.quantile(differences, [alpha, 1 - alpha]))
    return {"Gain": protected["F"] - baseline["F"], "95% CI": interval}


def sample_experiment(sources, model_id, *, noise_model, seed, acceptance="all",
                      ports=None, shots=SHOTS_PER_BASIS, resamples=BOOTSTRAP_RESAMPLES,
                      clifford_simulation=False, simulator_options=None,
                      native_circuits=None, source_compilation=None):
    """Compile, sample each basis, select syndromes, and retain reproducible records."""
    ports = PROCESSORS[model_id].ports if ports is None else ports
    native = (native_circuits if native_circuits is not None else
              {b: compile_optional(sources[b], model_id, seed=seed) for b in BASES})
    for circuit in native.values():
        verify_native(circuit, model_id, ports)
    method = ("stabilizer" if clifford_simulation else
              "density_matrix" if model_id == "ibm_today" else "matrix_product_state")
    options = {"max_parallel_threads": 1, **(simulator_options or {})}
    if method == "matrix_product_state":
        options.setdefault("matrix_product_state_truncation_threshold", 1e-12)
    if method == "density_matrix":
        # Aer truncates idle wires; these IBM circuits use at most eight qubits.
        # Per-shot execution samples each intermediate readout error separately.
        # Aer 0.17.2's shot branching shares those errors across a branch.
        options.setdefault("max_memory_mb", 512)
        for option in ("shot_branching_enable", "shot_branching_sampling_enable"):
            if options.get(option):
                raise ValueError("Aer 0.17.2 intermediate readout requires shot branching disabled")
            options[option] = False
    simulator = AerSimulator(method=method, noise_model=noise_model, **options)
    counts, seeds, simulation_metadata = {}, {}, {}
    for i, basis in enumerate(BASES):
        seeds[basis] = aer_seed(seed, basis)
        simulation = sources[basis] if clifford_simulation else native[basis]
        if clifford_simulation:
            # At optimization 0, every H/Sdg/Pauli here becomes one native u.
            # Matching depolarizing channels after those Cliffords give the same
            # circuit channel while Aer can sample stabilizer trajectories quickly.
            n_single = sum(op.name in {"h", "s", "sdg", "x", "y", "z"}
                           for op, _, _ in _instructions(simulation))
            assert native[basis].count_ops().get("u", 0) == n_single
        result = simulator.run(simulation, shots=shots, seed_simulator=seeds[basis]).result()
        if not result.success:
            raise RuntimeError(result.status)
        counts[basis] = result.get_counts()
        metadata = result.results[0].metadata
        assert metadata["method"] == method
        simulation_metadata[basis] = {
            "Method": metadata["method"], "Active qubits": metadata.get("num_qubits"),
            "Required memory MB": metadata.get("required_memory_mb"),
            "Noise representation": metadata.get("noise"),
        }
    stats = count_statistics(counts, acceptance, seed=seed + 10, resamples=resamples)
    costs = {b: resource_costs(native[b], sources[b]) for b in BASES}
    yield_ = stats["Yield"]
    total = sum(sum(c.values()) for c in counts.values())
    odd = sum(n for c in counts.values() for key, n in c.items()
              if sum(map(int, key.replace(" ", "")[::-1][2:])) % 2)
    return {
        **stats, "counts": counts, "costs": costs, "native_circuits": native,
        "simulation_metadata": simulation_metadata,
        "CX / accepted shot": costs["ZZ"]["Two-qubit gates"] / yield_ if yield_ else None,
        "Odd syndrome fraction": odd / total if total else None,
        "settings": {"Processor": model_id, "Ports": list(ports), "Shots per basis": shots,
                     "Simulator": method, "Simulator options": options, "Simulator seeds": seeds,
                     "Simulator seed rule": "52-bit SHA256(qccr-aer-v1:run_seed:basis)",
                     "Transpiler seed": seed if native_circuits is None else None,
                     "Optimization level": 0 if native_circuits is None else None,
                     "Source compilation": source_compilation,
                     "Initial layout": list(range(PROCESSORS[model_id].num_qubits)),
                     "Routing": "none; supplied physical edges", "Acceptance": acceptance,
                     "Bootstrap seed": seed + 10, "Bootstrap resamples": resamples,
                     "Confidence level": CONFIDENCE_LEVEL,
                     "Simulation basis": "Clifford equivalent" if clifford_simulation else "native"},
    }


def serializable_result(result):
    """Keep measured data and settings for export; circuits remain in the notebook."""
    return {key: value for key, value in result.items() if key != "native_circuits"}
