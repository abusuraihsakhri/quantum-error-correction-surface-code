"""
Surface Code Quantum Error Correction Engine
Real implementation using Python stdlib only.

Surface Code (Kitaev, 1997; Dennis et al., 2002):
- 2D lattice of data qubits and syndrome (ancilla) qubits
- X-stabilizers detect Z errors (bit flips)
- Z-stabilizers detect X errors (phase flips)
- Code distance d: corrects up to (d-1)/2 errors
- Threshold error rate: ~1% for independent depolarizing noise

Lattice structure (distance d):
- d² data qubits on edges
- (d²-1) X-stabilizers and (d²-1) Z-stabilizers
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
from typing import List, Tuple, Dict, Optional, Set, Any


# ─── Surface Code Lattice ───────────────────────────────────────────────────

class SurfaceCodeLattice:
    """
    Represents a rotated surface code of distance d.
    
    Data qubits are placed on edges of a d×d grid.
    X-stabilizers (faces) detect Z errors.
    Z-stabilizers (faces) detect X errors.
    """
    
    def __init__(self, distance: int):
        if distance < 3 or distance % 2 == 0:
            raise ValueError("Distance must be odd and >= 3")
        self.d = distance
        self.n_data = distance * distance
        self.n_stabilizers = distance * distance - 1
        
        # Data qubit positions: (row, col) on d×d grid
        self.data_qubits = []
        for r in range(distance):
            for c in range(distance):
                self.data_qubits.append((r, c))
        
        # X-stabilizers: plaquettes
        self.x_stabilizers = self._build_x_stabilizers()
        
        # Z-stabilizers: vertices
        self.z_stabilizers = self._build_z_stabilizers()
        
        # Logical operators
        self.logical_x = self._build_logical_x()
        self.logical_z = self._build_logical_z()
    
    def _build_x_stabilizers(self) -> List[List[int]]:
        """Build X-stabilizer generators (face operators)."""
        stabilizers = []
        d = self.d
        for r in range(d - 1):
            for c in range(d - 1):
                # Each face touches 4 data qubits
                qubits = [
                    self._data_index(r, c),
                    self._data_index(r, c + 1),
                    self._data_index(r + 1, c),
                    self._data_index(r + 1, c + 1),
                ]
                stabilizers.append(qubits)
        return stabilizers
    
    def _build_z_stabilizers(self) -> List[List[int]]:
        """Build Z-stabilizer generators (vertex operators)."""
        stabilizers = []
        d = self.d
        for r in range(d):
            for c in range(d):
                # Each vertex touches up to 4 data qubits
                qubits = []
                if r > 0:
                    qubits.append(self._data_index(r - 1, c))
                if r < d - 1:
                    qubits.append(self._data_index(r, c))
                if c > 0:
                    qubits.append(self._data_index(r, c - 1))
                if c < d - 1:
                    qubits.append(self._data_index(r, c))
                
                # Remove duplicates and ensure at least 2 qubits
                qubits = list(set(qubits))
                if len(qubits) >= 2:
                    stabilizers.append(qubits)
        
        return stabilizers
    
    def _data_index(self, row: int, col: int) -> int:
        """Convert (row, col) to data qubit index."""
        return row * self.d + col
    
    def _build_logical_x(self) -> List[int]:
        """Build logical X operator (horizontal string)."""
        # Logical X: string of X operators across a row
        return [self._data_index(0, c) for c in range(self.d)]
    
    def _build_logical_z(self) -> List[int]:
        """Build logical Z operator (vertical string)."""
        # Logical Z: string of Z operators down a column
        return [self._data_index(r, 0) for r in range(self.d)]
    
    def get_data_qubit(self, index: int) -> Tuple[int, int]:
        """Get (row, col) of data qubit by index."""
        return self.data_qubits[index]


# ─── Error Model ─────────────────────────────────────────────────────────────

def apply_depolarizing_noise(n_qubits: int, error_rate: float) -> List[int]:
    """
    Apply independent depolarizing noise to data qubits.
    
    Returns error vector: 0 = no error, 1 = X error, 2 = Z error, 3 = Y error
    """
    errors = [0] * n_qubits
    for i in range(n_qubits):
        if random.random() < error_rate:
            # Choose error type uniformly
            errors[i] = random.choice([1, 2, 3])
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


# ─── Minimum Weight Perfect Matching (Simplified) ───────────────────────────

def minimum_weight_matching(defects: List[int], n_stabilizers: int,
                             stabilizers: List[List[int]]) -> List[Tuple[int, int]]:
    """
    Simplified minimum weight perfect matching.
    
    Pairs up defects (syndrome violations) using nearest-neighbor matching.
    Returns list of matched pairs.
    """
    if len(defects) % 2 != 0:
        # Odd number of defects - add boundary
        defects = defects + [n_stabilizers]  # virtual boundary defect
    
    if len(defects) == 0:
        return []
    
    # Greedy nearest-neighbor matching
    remaining = list(defects)
    matches = []
    
    while len(remaining) >= 2:
        best_dist = float('inf')
        best_pair = (0, 1)
        
        for i in range(len(remaining)):
            for j in range(i + 1, len(remaining)):
                dist = _defect_distance(remaining[i], remaining[j], n_stabilizers)
                if dist < best_dist:
                    best_dist = dist
                    best_pair = (i, j)
        
        i, j = best_pair
        matches.append((remaining[i], remaining[j]))
        # Remove matched defects (remove higher index first)
        remaining.pop(max(i, j))
        remaining.pop(min(i, j))
    
    return matches


def _defect_distance(d1: int, d2: int, n_stabilizers: int) -> int:
    """Calculate Manhattan distance between two defects."""
    if d1 == n_stabilizers or d2 == n_stabilizers:
        # Boundary defect
        return 1
    # Simple approximation: use index difference
    return abs(d1 - d2)


def matching_to_correction(matches: List[Tuple[int, int]], stabilizers: List[List[int]],
                            n_data: int, stabilizer_type: str) -> List[int]:
    """
    Convert matching to correction operations.
    
    For each matched pair, apply correction along the path between them.
    Returns correction vector (same format as error vector).
    """
    correction = [0] * n_data
    
    for d1, d2 in matches:
        # Find path between defects and apply correction
        # Simplified: apply correction on qubits shared by both stabilizers
        if d1 < len(stabilizers) and d2 < len(stabilizers):
            stab1 = set(stabilizers[d1])
            stab2 = set(stabilizers[d2])
            shared = stab1 & stab2
            
            for qubit_idx in shared:
                if stabilizer_type == 'X':
                    # Apply Z correction
                    correction[qubit_idx] = 2
                else:
                    # Apply X correction
                    correction[qubit_idx] = 1
    
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

def error_correction_cycle(distance: int, error_rate: float,
                            seed: Optional[int] = None) -> dict:
    """
    Run a single error correction cycle.

    1. Create surface code lattice
    2. Apply depolarizing noise
    3. Extract syndromes
    4. Decode with matching
    5. Apply correction
    6. Check for logical error
    """
    if not isinstance(distance, int) or distance < 3 or distance % 2 == 0:
        raise ValueError("Distance must be an odd integer >= 3")
    if not isinstance(error_rate, (int, float)) or error_rate < 0 or error_rate > 1:
        raise ValueError("Error rate must be a float between 0 and 1")
    if seed is not None and not isinstance(seed, int):
        raise TypeError("Seed must be an integer or None")

    if seed is not None:
        random.seed(seed)
    
    # Create lattice
    lattice = SurfaceCodeLattice(distance)
    
    # Apply noise
    errors = apply_depolarizing_noise(lattice.n_data, error_rate)
    n_errors = sum(1 for e in errors if e != 0)
    
    # Extract syndromes
    x_syndrome = extract_syndrome(errors, lattice.x_stabilizers, 'X')
    z_syndrome = extract_syndrome(errors, lattice.z_stabilizers, 'Z')
    
    x_defects = syndrome_to_defects(x_syndrome)
    z_defects = syndrome_to_defects(z_syndrome)
    
    # Decode with matching
    x_matches = minimum_weight_matching(x_defects, len(lattice.x_stabilizers), lattice.x_stabilizers)
    z_matches = minimum_weight_matching(z_defects, len(lattice.z_stabilizers), lattice.z_stabilizers)
    
    # Get corrections
    x_correction = matching_to_correction(x_matches, lattice.x_stabilizers, lattice.n_data, 'X')
    z_correction = matching_to_correction(z_matches, lattice.z_stabilizers, lattice.n_data, 'Z')
    
    # Combine corrections
    correction = [0] * lattice.n_data
    for i in range(lattice.n_data):
        correction[i] = _combine_pauli(x_correction[i], z_correction[i])
    
    # Check logical errors
    logical_x_error = check_logical_error(errors, correction, lattice.logical_x, 'X')
    logical_z_error = check_logical_error(errors, correction, lattice.logical_z, 'Z')
    logical_error = logical_x_error or logical_z_error
    
    return {
        'distance': distance,
        'error_rate': error_rate,
        'n_data_qubits': lattice.n_data,
        'n_stabilizers': lattice.n_stabilizers,
        'n_errors': n_errors,
        'x_syndrome_weight': sum(x_syndrome),
        'z_syndrome_weight': sum(z_syndrome),
        'x_defects': x_defects,
        'z_defects': z_defects,
        'x_matches': x_matches,
        'z_matches': z_matches,
        'logical_x_error': logical_x_error,
        'logical_z_error': logical_z_error,
        'logical_error': logical_error,
        'correction_applied': any(c != 0 for c in correction),
    }


# ─── Logical Error Rate Calculation ─────────────────────────────────────────

def calculate_logical_error_rate(distance: int, error_rate: float,
                                   n_trials: int = 1000,
                                   seed: int = 42) -> dict:
    """
    Calculate logical error rate by running many error correction cycles.
    """
    if not isinstance(distance, int) or distance < 3 or distance % 2 == 0:
        raise ValueError("Distance must be an odd integer >= 3")
    if not isinstance(error_rate, (int, float)) or error_rate < 0 or error_rate > 1:
        raise ValueError("Error rate must be a float between 0 and 1")
    if not isinstance(n_trials, int) or n_trials < 1:
        raise ValueError("Number of trials must be a positive integer")
    random.seed(seed)
    
    logical_errors = 0
    x_errors = 0
    z_errors = 0
    
    for _ in range(n_trials):
        result = error_correction_cycle(distance, error_rate)
        if result['logical_error']:
            logical_errors += 1
        if result['logical_x_error']:
            x_errors += 1
        if result['logical_z_error']:
            z_errors += 1
    
    logical_error_rate = logical_errors / n_trials
    
    return {
        'distance': distance,
        'physical_error_rate': error_rate,
        'n_trials': n_trials,
        'logical_error_rate': logical_error_rate,
        'logical_x_error_rate': x_errors / n_trials,
        'logical_z_error_rate': z_errors / n_trials,
        'below_threshold': logical_error_rate < error_rate,
        'suppression_factor': error_rate / logical_error_rate if logical_error_rate > 0 else float('inf'),
    }


def threshold_estimation(distance: int, n_trials: int = 500,
                           seed: int = 42) -> dict:
    """
    Estimate the threshold error rate for a given code distance.

    The threshold is the physical error rate below which the logical
    error rate is suppressed.
    """
    if not isinstance(distance, int) or distance < 3 or distance % 2 == 0:
        raise ValueError("Distance must be an odd integer >= 3")
    if not isinstance(n_trials, int) or n_trials < 1:
        raise ValueError("Number of trials must be a positive integer")
    random.seed(seed)
    
    # Test multiple physical error rates
    test_rates = [0.001, 0.002, 0.005, 0.01, 0.02, 0.03, 0.05, 0.1]
    results = []
    
    for rate in test_rates:
        result = calculate_logical_error_rate(distance, rate, n_trials=n_trials)
        results.append(result)
    
    # Find crossing point (where logical rate ≈ physical rate)
    threshold = 0.01  # default estimate
    for r in results:
        if r['logical_error_rate'] < r['physical_error_rate']:
            threshold = r['physical_error_rate']
    
    return {
        'distance': distance,
        'n_trials_per_rate': n_trials,
        'test_rates': test_rates,
        'results': results,
        'estimated_threshold': threshold,
    }


# ─── Code Properties ────────────────────────────────────────────────────────

def code_properties(distance: int) -> dict:
    """Return properties of the surface code for given distance."""
    n_data = distance * distance
    n_stabilizers = n_data - 1
    max_correctable = (distance - 1) // 2
    
    return {
        'distance': distance,
        'n_data_qubits': n_data,
        'n_stabilizers': n_stabilizers,
        'max_correctable_errors': max_correctable,
        'code_rate': 1 / n_data,  # 1 logical qubit per n_data physical qubits
        'overhead': n_data,
        'threshold_estimate': 0.01,  # ~1% for surface codes
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
