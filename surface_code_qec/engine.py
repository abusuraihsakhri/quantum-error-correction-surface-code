"""
Surface Code Quantum Error Correction Engine
Real implementation using Python stdlib only.

Surface Code (Kitaev, 1997; Dennis et al., 2002):
- 2D lattice of data qubits and syndrome (ancilla) qubits
- X-stabilizers detect Z (phase-flip) errors
- Z-stabilizers detect X (bit-flip) errors
- Code distance d: corrects up to (d-1)/2 errors
- Threshold error rate: ~1% for independent depolarizing noise

Lattice structure (distance d):
- d² data qubits at grid vertices
- (d²-1)/2 X-stabilizers and (d²-1)/2 Z-stabilizers
- Logical operators span the lattice

Syndrome extraction:
1. Apply noise to data qubits
2. Measure stabilizers to get syndrome
3. Decode syndrome using minimum weight perfect matching (simplified)
4. Apply correction
5. Check if logical error occurred
"""
import math
import random
from collections import deque
from functools import lru_cache
from typing import List, Tuple, Dict, Optional, Set, Any


# ─── Surface Code Lattice ───────────────────────────────────────────────────

class SurfaceCodeLattice:
    """Rotated planar [[d², 1, d]] surface code with d² data qubits.

    Interior checkerboard plaquettes have weight four; alternating
    boundary checks have weight two. Each X check commutes with every
    Z check. Logical X is the top row; logical Z is the left column.
    """

    def __init__(self, distance: int):
        if isinstance(distance, bool) or not isinstance(distance, int) or distance < 3 or distance % 2 == 0 or distance > 21:
            raise ValueError("Distance must be an odd integer between 3 and 21")
        self.d = distance
        self.n_data = distance * distance
        self.data_qubits = [(r, c) for r in range(distance) for c in range(distance)]
        self.x_stabilizers = self._build_stabilizers("X")
        self.z_stabilizers = self._build_stabilizers("Z")
        self.n_stabilizers = len(self.x_stabilizers) + len(self.z_stabilizers)
        self.logical_x = [self._data_index(0, c) for c in range(distance)]
        self.logical_z = [self._data_index(r, 0) for r in range(distance)]

    def _data_index(self, row: int, col: int) -> int:
        return row * self.d + col

    def _build_stabilizers(self, kind: str) -> List[List[int]]:
        d = self.d
        stabs = []
        parity = 0 if kind == "X" else 1
        for r in range(d - 1):
            for c in range(d - 1):
                if (r + c) % 2 == parity:
                    stabs.append([self._data_index(rr, cc)
                                  for rr in (r, r + 1) for cc in (c, c + 1)])
        if kind == "X":
            for r in range(d - 1):
                c = 0 if r % 2 else d - 1
                stabs.append([self._data_index(r, c), self._data_index(r + 1, c)])
        else:
            for c in range(d - 1):
                r = 0 if c % 2 == 0 else d - 1
                stabs.append([self._data_index(r, c), self._data_index(r, c + 1)])
        return stabs

    def get_data_qubit(self, index: int) -> Tuple[int, int]:
        return self.data_qubits[index]




# ─── Error Model ─────────────────────────────────────────────────────────────

def apply_depolarizing_noise(n_qubits: int, error_rate: float, rng=None) -> List[int]:
    """
    Apply independent depolarizing noise to data qubits.
    
    Returns error vector: 0 = no error, 1 = X error, 2 = Z error, 3 = Y error
    """
    if not isinstance(n_qubits, int) or n_qubits < 0 or n_qubits > 100000:
        raise ValueError('Invalid number of qubits')
    _validate_rate(error_rate)
    rng = rng if rng is not None else random
    errors = [0] * n_qubits
    for i in range(n_qubits):
        if rng.random() < error_rate:
            errors[i] = rng.choice([1, 2, 3])
    return errors


def error_to_pauli(error: int) -> str:
    """Convert error code to Pauli string."""
    return {0: 'I', 1: 'X', 2: 'Z', 3: 'Y'}[error]


# ─── Syndrome Extraction ────────────────────────────────────────────────────

def extract_syndrome(errors: List[int], stabilizers: List[List[int]],
                      stabilizer_type: str) -> List[int]:
    """
    Extract syndrome from error configuration.
    
    For X-stabilizers: detect Z errors (error codes 2, 3)
    For Z-stabilizers: detect X errors (error codes 1, 3)
    
    Returns syndrome vector: 0 = no detection, 1 = detection
    """
    syndrome = []
    for stab in stabilizers:
        parity = 0
        for qubit_idx in stab:
            if stabilizer_type == 'X':
                # X-stabilizer detects Z errors
                if errors[qubit_idx] in [2, 3]:  # Z or Y
                    parity ^= 1
            else:  # Z-stabilizer
                # Z-stabilizer detects X errors
                if errors[qubit_idx] in [1, 3]:  # X or Y
                    parity ^= 1
        syndrome.append(parity)
    return syndrome


def syndrome_to_defects(syndrome: List[int]) -> List[int]:
    """Convert syndrome to list of defect positions (where syndrome=1)."""
    return [i for i, s in enumerate(syndrome) if s == 1]


# ─── Syndrome graph decoder ─────────────────────────────────────────────────

def _syndrome_graph(stabilizers: List[List[int]]):
    """Check-node graph; each physical qubit labels one edge to a check or boundary."""
    adjacent = [[] for _ in stabilizers]
    boundaries = [[] for _ in stabilizers]
    incidence = {}
    for idx, stab in enumerate(stabilizers):
        for q in stab:
            incidence.setdefault(q, []).append(idx)
    for q, checks in incidence.items():
        if len(checks) == 1:
            boundaries[checks[0]].append(q)
        elif len(checks) == 2:
            a, b = checks
            adjacent[a].append((b, q))
            adjacent[b].append((a, q))
        else:
            raise ValueError("Invalid check geometry: a qubit belongs to >2 checks")
    return adjacent, boundaries


def _shortest_paths(start: int, adjacent):
    distance = {start: 0}
    previous = {}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for next_node, qubit in adjacent[node]:
            if next_node not in distance:
                distance[next_node] = distance[node] + 1
                previous[next_node] = (node, qubit)
                queue.append(next_node)
    return distance, previous


def _path_to(start, target, previous):
    path = []
    while target != start:
        parent, qubit = previous[target]
        path.append(qubit)
        target = parent
    return path


def _boundary_path(start, distance, previous, boundaries):
    choices = [(distance[node] + 1, node, min(qubits))
               for node, qubits in enumerate(boundaries)
               if qubits and node in distance]
    if not choices:
        raise ValueError("Syndrome check has no path to a boundary")
    _, node, qubit = min(choices)
    return _path_to(start, node, previous) + [qubit]


def minimum_weight_matching(defects: List[int], n_stabilizers: int,
                            stabilizers: List[List[int]]) -> List[Tuple[int, int]]:
    """Exact defect/boundary minimum-weight matching up to 18 defects.

    For larger syndromes, uses a bounded greedy approximation instead of
    claiming a Blossom or globally optimal MWPM result. The boundary is
    represented by the virtual check index n_stabilizers.
    """
    if not defects:
        return []
    if n_stabilizers != len(stabilizers) or any(
            not isinstance(i, int) or i < 0 or i >= n_stabilizers for i in defects):
        raise ValueError("Invalid defect indices or check count")
    if len(set(defects)) != len(defects):
        raise ValueError("Duplicate defects")
    adjacent, boundaries = _syndrome_graph(stabilizers)
    distances = []
    boundary_costs = []
    for defect in defects:
        dist, prev = _shortest_paths(defect, adjacent)
        distances.append(dist)
        boundary_costs.append(len(_boundary_path(defect, dist, prev, boundaries)))
    n = len(defects)
    if n > 18:
        remaining = list(range(n))
        matches = []
        while remaining:
            i = remaining.pop(0)
            partner = min(remaining, key=lambda j: (distances[i].get(defects[j], math.inf), j), default=None)
            if partner is not None and distances[i].get(defects[partner], math.inf) < boundary_costs[i]:
                matches.append((defects[i], defects[partner]))
                remaining.remove(partner)
            else:
                matches.append((defects[i], n_stabilizers))
        return matches

    decision = {}
    @lru_cache(maxsize=None)
    def optimal(mask):
        if mask == 0:
            return 0
        bit = mask & -mask
        i = bit.bit_length() - 1
        rest = mask ^ bit
        best = boundary_costs[i] + optimal(rest)
        selected = None
        for j in range(i + 1, n):
            if rest & (1 << j):
                cost = distances[i].get(defects[j], math.inf) + optimal(rest ^ (1 << j))
                if cost < best:
                    best, selected = cost, j
        decision[mask] = (i, selected)
        return best
    mask = (1 << n) - 1
    optimal(mask)
    matches = []
    while mask:
        i, j = decision[mask]
        mask ^= (1 << i)
        if j is None:
            matches.append((defects[i], n_stabilizers))
        else:
            matches.append((defects[i], defects[j]))
            mask ^= (1 << j)
    return matches


def matching_to_correction(matches: List[Tuple[int, int]],
                           stabilizers: List[List[int]], n_data: int,
                           stabilizer_type: str) -> List[int]:
    """Construct a correction along shortest check-to-check or boundary paths."""
    if stabilizer_type not in ("X", "Z"):
        raise ValueError("Stabilizer type must be X or Z")
    adjacent, boundaries = _syndrome_graph(stabilizers)
    correction = [0] * n_data
    virtual = len(stabilizers)
    pauli = 2 if stabilizer_type == "X" else 1
    for a, b in matches:
        if not 0 <= a < virtual or not 0 <= b <= virtual:
            raise ValueError("Invalid match endpoint")
        distance, previous = _shortest_paths(a, adjacent)
        path = (_boundary_path(a, distance, previous, boundaries)
                if b == virtual else _path_to(a, b, previous))
        for q in path:
            correction[q] = _combine_pauli(correction[q], pauli)
    return correction




# ─── Logical Error Check ────────────────────────────────────────────────────

def check_logical_error(errors: List[int], correction: List[int],
                         logical_op: List[int], op_type: str) -> bool:
    """
    Check if a logical error occurred.
    
    A logical error occurs if the combined error+correction anticommutes
    with the logical operator.
    """
    # Combine errors and correction
    combined = [0] * len(errors)
    for i in range(len(errors)):
        combined[i] = _combine_pauli(errors[i], correction[i])
    
    # Count anticommuting Paulis on logical operator qubits
    anticommutations = 0
    for qubit_idx in logical_op:
        if op_type == 'X':
            # Logical X anticommutes with Z errors
            if combined[qubit_idx] in [2, 3]:  # Z or Y
                anticommutations += 1
        else:  # Z
            # Logical Z anticommutes with X errors
            if combined[qubit_idx] in [1, 3]:  # X or Y
                anticommutations += 1
    
    # Odd number of anticommutations = logical error
    return anticommutations % 2 == 1


def _combine_pauli(p1: int, p2: int) -> int:
    """Combine two Pauli operators (0=I, 1=X, 2=Z, 3=Y)."""
    # Pauli multiplication table
    table = {
        (0, 0): 0, (0, 1): 1, (0, 2): 2, (0, 3): 3,
        (1, 0): 1, (1, 1): 0, (1, 2): 3, (1, 3): 2,
        (2, 0): 2, (2, 1): 3, (2, 2): 0, (2, 3): 1,
        (3, 0): 3, (3, 1): 2, (3, 2): 1, (3, 3): 0,
    }
    return table[(p1, p2)]


# ─── Full Error Correction Cycle ────────────────────────────────────────────

def _validate_rate(rate):
    if (isinstance(rate, bool) or not isinstance(rate, (int, float))
            or not math.isfinite(rate) or rate < 0 or rate > 1):
        raise ValueError("Error rate must be finite and between 0 and 1")


def error_correction_cycle(distance: int, error_rate: float,
                           seed: Optional[int] = None, rng=None) -> dict:
    """Apply independent data-qubit depolarizing noise and decode one ideal round."""
    lattice = SurfaceCodeLattice(distance)
    _validate_rate(error_rate)
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise TypeError("Seed must be an integer or None")
    if rng is not None and seed is not None:
        raise ValueError("Supply seed or rng, not both")
    rng = rng if rng is not None else random.Random(seed)
    errors = apply_depolarizing_noise(lattice.n_data, error_rate, rng)
    x_syn = extract_syndrome(errors, lattice.x_stabilizers, "X")
    z_syn = extract_syndrome(errors, lattice.z_stabilizers, "Z")
    x_defects = syndrome_to_defects(x_syn)
    z_defects = syndrome_to_defects(z_syn)
    x_matches = minimum_weight_matching(x_defects, len(lattice.x_stabilizers), lattice.x_stabilizers)
    z_matches = minimum_weight_matching(z_defects, len(lattice.z_stabilizers), lattice.z_stabilizers)
    x_correction = matching_to_correction(x_matches, lattice.x_stabilizers, lattice.n_data, "X")
    z_correction = matching_to_correction(z_matches, lattice.z_stabilizers, lattice.n_data, "Z")
    correction = [_combine_pauli(a, b) for a, b in zip(x_correction, z_correction)]
    residual = [_combine_pauli(a, b) for a, b in zip(errors, correction)]
    remaining_x = extract_syndrome(residual, lattice.x_stabilizers, "X")
    remaining_z = extract_syndrome(residual, lattice.z_stabilizers, "Z")
    if any(remaining_x) or any(remaining_z):
        raise RuntimeError("Decoder did not clear all measured syndromes")
    logical_x = check_logical_error(errors, correction, lattice.logical_x, "X")
    logical_z = check_logical_error(errors, correction, lattice.logical_z, "Z")
    return {
        "distance": distance, "error_rate": error_rate,
        "n_data_qubits": lattice.n_data, "n_stabilizers": lattice.n_stabilizers,
        "n_errors": sum(e != 0 for e in errors),
        "x_syndrome_weight": sum(x_syn), "z_syndrome_weight": sum(z_syn),
        "x_defects": x_defects, "z_defects": z_defects,
        "x_matches": x_matches, "z_matches": z_matches,
        "logical_x_error": logical_x, "logical_z_error": logical_z,
        "logical_error": logical_x or logical_z,
        "correction_applied": any(c != 0 for c in correction),
        "residual_syndrome_weight": sum(remaining_x) + sum(remaining_z),
        "decoder": ("exact" if max(len(x_defects), len(z_defects)) <= 18
                    else "greedy_approximation"),
    }




# ─── Logical Error Rate Calculation ─────────────────────────────────────────

def calculate_logical_error_rate(distance: int, error_rate: float,
                                 n_trials: int = 1000, seed: int = 42) -> dict:
    """Monte Carlo logical failure fraction under ideal syndrome measurements."""
    SurfaceCodeLattice(distance)
    _validate_rate(error_rate)
    if isinstance(n_trials, bool) or not isinstance(n_trials, int) or not 1 <= n_trials <= 100000:
        raise ValueError("Trials must be an integer from 1 to 100000")
    rng = random.Random(seed)
    logical_errors = x_errors = z_errors = 0
    for _ in range(n_trials):
        result = error_correction_cycle(distance, error_rate, rng=rng)
        logical_errors += result["logical_error"]
        x_errors += result["logical_x_error"]
        z_errors += result["logical_z_error"]
    logical_rate = logical_errors / n_trials
    return {
        "distance": distance, "physical_error_rate": error_rate,
        "n_trials": n_trials, "logical_error_rate": logical_rate,
        "logical_x_error_rate": x_errors / n_trials,
        "logical_z_error_rate": z_errors / n_trials,
        "below_threshold": logical_rate < error_rate,  # legacy key; NOT a threshold measurement
        "logical_rate_below_physical": logical_rate < error_rate,
        "suppression_factor": (error_rate / logical_rate if logical_rate
                               else None if error_rate else 1.0),
    }


def threshold_estimation(distance: int, n_trials: int = 500,
                         seed: int = 42) -> dict:
    """Sample suppression at fixed distance; a true code threshold requires crossings across distances."""
    SurfaceCodeLattice(distance)
    if isinstance(n_trials, bool) or not isinstance(n_trials, int) or not 1 <= n_trials <= 100000:
        raise ValueError("Trials must be an integer from 1 to 100000")
    rates = [0.001, 0.002, 0.005, 0.01, 0.02, 0.03, 0.05, 0.1]
    results = [calculate_logical_error_rate(distance, rate, n_trials, seed + i)
               for i, rate in enumerate(rates)]
    return {
        "distance": distance, "n_trials_per_rate": n_trials,
        "test_rates": rates, "results": results,
        "estimated_threshold": None,
        "note": "A threshold cannot be inferred from one code distance; compare logical-rate curves for multiple distances.",
    }




# ─── Code Properties ────────────────────────────────────────────────────────

def code_properties(distance: int) -> dict:
    """Return properties of the surface code for given distance."""
    lattice = SurfaceCodeLattice(distance)
    n_data = lattice.n_data
    n_stabilizers = lattice.n_stabilizers
    max_correctable = (distance - 1) // 2
    
    return {
        'distance': distance,
        'n_data_qubits': n_data,
        'n_stabilizers': n_stabilizers,
        'max_correctable_errors': max_correctable,
        'code_rate': 1 / n_data,  # 1 logical qubit per n_data physical qubits
        'overhead': n_data,
        'threshold_estimate': None,  # cannot infer a threshold from code geometry
    }


# ─── Frontier Domain Engine (Agent System Integration) ──────────────────────

class FrontierDomainEngine:
    """
    Evaluation engine for agent-system payload processing.
    Provides threshold-based analysis of domain metrics.
    """

    # Threshold constants for surface code quality metrics
    PRIMARY_THRESHOLD = 25.0
    PRIMARY_CRITICAL_THRESHOLD = 50.0
    SECONDARY_THRESHOLD = 12.0
    SECONDARY_CRITICAL_THRESHOLD = 20.0

    @classmethod
    def evaluate_primary_parameter(cls, value: float) -> Optional[Dict[str, str]]:
        """Evaluate primary metric against surface code thresholds."""
        if value > cls.PRIMARY_CRITICAL_THRESHOLD:
            return {
                "summary": "Critical primary parameter exceeded",
                "details": f"Primary metric ({value:.2f}) exceeds critical threshold ({cls.PRIMARY_CRITICAL_THRESHOLD:.2f})",
                "remediation": "Immediate review required: check physical error rates and decoder configuration.",
            }
        elif value > cls.PRIMARY_THRESHOLD:
            return {
                "summary": "Elevated primary parameter detected",
                "details": f"Primary metric ({value:.2f}) exceeds reference bound ({cls.PRIMARY_THRESHOLD:.2f})",
                "remediation": "Review surface code distance and stabilizer measurement protocols.",
            }
        return None

    @classmethod
    def evaluate_secondary_kinetics(cls, value: float, is_critical: bool) -> Optional[Dict[str, str]]:
        """Evaluate secondary kinetics metric."""
        if is_critical or value > cls.SECONDARY_CRITICAL_THRESHOLD:
            return {
                "summary": "Critical secondary kinetics threshold breached",
                "details": f"Secondary metric ({value:.2f}) with critical flag={is_critical} requires immediate intervention.",
                "remediation": "Execute emergency error correction cycle and recalibrate decoder weights.",
            }
        elif value > cls.SECONDARY_THRESHOLD:
            return {
                "summary": "Elevated secondary kinetics detected",
                "details": f"Secondary metric ({value:.2f}) exceeds normal operating range ({cls.SECONDARY_THRESHOLD:.2f}).",
                "remediation": "Increase monitoring frequency and verify syndrome extraction integrity.",
            }
        return None

    @classmethod
    def audit_specification_conformance(cls, status_descriptor: str, attributes: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Audit status descriptor for specification conformance."""
        desc_upper = str(status_descriptor).upper()
        anomaly_keywords = {"DISCORDANT", "ANOMALY", "MUTANT", "VIOLATION", "FAIL", "REJECT", "DEVIATION"}

        if any(keyword in desc_upper for keyword in anomaly_keywords):
            return {
                "summary": "Specification conformance anomaly detected",
                "details": f"Status descriptor '{status_descriptor}' indicates deviation from fault-tolerant specifications.",
                "remediation": "Re-evaluate syndrome extraction and verify code distance parameters.",
            }
        return None
