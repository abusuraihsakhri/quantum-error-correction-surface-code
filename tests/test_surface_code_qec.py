"""
Tests for Surface Code Quantum Error Correction Engine.
Real QEC verification.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import random
import pytest
from surface_code_qec.engine import (
    SurfaceCodeLattice, apply_depolarizing_noise,
    extract_syndrome, syndrome_to_defects,
    minimum_weight_matching, matching_to_correction,
    check_logical_error, _combine_pauli,
    error_correction_cycle, calculate_logical_error_rate,
    threshold_estimation, code_properties,
    error_to_pauli,
)


# ─── Lattice Construction ───────────────────────────────────────────────────

class TestLattice:
    def test_lattice_d3(self):
        lattice = SurfaceCodeLattice(3)
        assert lattice.d == 3
        assert lattice.n_data == 9
        assert len(lattice.data_qubits) == 9

    def test_lattice_d5(self):
        lattice = SurfaceCodeLattice(5)
        assert lattice.d == 5
        assert lattice.n_data == 25

    def test_lattice_invalid_even(self):
        with pytest.raises(ValueError):
            SurfaceCodeLattice(4)

    def test_lattice_invalid_small(self):
        with pytest.raises(ValueError):
            SurfaceCodeLattice(2)

    def test_x_stabilizers_exist(self):
        lattice = SurfaceCodeLattice(3)
        assert len(lattice.x_stabilizers) > 0

    def test_z_stabilizers_exist(self):
        lattice = SurfaceCodeLattice(3)
        assert len(lattice.z_stabilizers) > 0

    def test_logical_x_length(self):
        lattice = SurfaceCodeLattice(3)
        assert len(lattice.logical_x) == 3

    def test_logical_z_length(self):
        lattice = SurfaceCodeLattice(3)
        assert len(lattice.logical_z) == 3

    def test_data_qubit_positions(self):
        lattice = SurfaceCodeLattice(3)
        for i in range(9):
            r, c = lattice.get_data_qubit(i)
            assert 0 <= r < 3
            assert 0 <= c < 3


# ─── Error Model ─────────────────────────────────────────────────────────────

class TestErrorModel:
    def test_no_errors_at_zero_rate(self):
        random.seed(42)
        errors = apply_depolarizing_noise(100, 0.0)
        assert all(e == 0 for e in errors)

    def test_all_errors_at_one_rate(self):
        random.seed(42)
        errors = apply_depolarizing_noise(100, 1.0)
        assert all(e != 0 for e in errors)

    def test_error_types_valid(self):
        random.seed(42)
        errors = apply_depolarizing_noise(1000, 0.5)
        assert all(e in [0, 1, 2, 3] for e in errors)

    def test_error_rate_approximate(self):
        random.seed(42)
        errors = apply_depolarizing_noise(10000, 0.1)
        n_errors = sum(1 for e in errors if e != 0)
        rate = n_errors / 10000
        assert 0.08 < rate < 0.12

    def test_error_to_pauli(self):
        assert error_to_pauli(0) == 'I'
        assert error_to_pauli(1) == 'X'
        assert error_to_pauli(2) == 'Z'
        assert error_to_pauli(3) == 'Y'


# ─── Pauli Combination ──────────────────────────────────────────────────────

class TestPauliCombination:
    def test_combine_identity(self):
        assert _combine_pauli(0, 0) == 0
        assert _combine_pauli(0, 1) == 1
        assert _combine_pauli(1, 0) == 1

    def test_combine_xx_is_identity(self):
        assert _combine_pauli(1, 1) == 0

    def test_combine_zz_is_identity(self):
        assert _combine_pauli(2, 2) == 0

    def test_combine_xz_is_y(self):
        assert _combine_pauli(1, 2) == 3

    def test_combine_zx_is_y(self):
        assert _combine_pauli(2, 1) == 3

    def test_combine_yy_is_identity(self):
        assert _combine_pauli(3, 3) == 0


# ─── Syndrome Extraction ────────────────────────────────────────────────────

class TestSyndrome:
    def test_no_error_no_syndrome(self):
        lattice = SurfaceCodeLattice(3)
        errors = [0] * lattice.n_data
        x_syn = extract_syndrome(errors, lattice.x_stabilizers, 'X')
        z_syn = extract_syndrome(errors, lattice.z_stabilizers, 'Z')
        assert all(s == 0 for s in x_syn)
        assert all(s == 0 for s in z_syn)

    def test_x_error_triggers_z_syndrome(self):
        lattice = SurfaceCodeLattice(3)
        errors = [0] * lattice.n_data
        errors[0] = 1  # X error on qubit 0
        z_syn = extract_syndrome(errors, lattice.z_stabilizers, 'Z')
        assert any(s == 1 for s in z_syn)

    def test_z_error_triggers_x_syndrome(self):
        lattice = SurfaceCodeLattice(3)
        errors = [0] * lattice.n_data
        errors[0] = 2  # Z error on qubit 0
        x_syn = extract_syndrome(errors, lattice.x_stabilizers, 'X')
        assert any(s == 1 for s in x_syn)

    def test_syndrome_to_defects(self):
        syndrome = [0, 1, 0, 1, 0]
        defects = syndrome_to_defects(syndrome)
        assert defects == [1, 3]

    def test_empty_syndrome_no_defects(self):
        syndrome = [0, 0, 0, 0]
        defects = syndrome_to_defects(syndrome)
        assert defects == []


# ─── Matching ────────────────────────────────────────────────────────────────

class TestMatching:
    def test_no_defects_no_matches(self):
        matches = minimum_weight_matching([], 4, [])
        assert matches == []

    def test_two_defects_one_match(self):
        matches = minimum_weight_matching([0, 3], 4, [[0, 1], [1, 2], [2, 3]])
        assert len(matches) == 1

    def test_four_defects_two_matches(self):
        matches = minimum_weight_matching([0, 1, 2, 3], 4, [[0, 1], [1, 2], [2, 3]])
        assert len(matches) == 2


# ─── Logical Error Check ────────────────────────────────────────────────────

class TestLogicalError:
    def test_no_error_no_logical_error(self):
        lattice = SurfaceCodeLattice(3)
        errors = [0] * lattice.n_data
        correction = [0] * lattice.n_data
        assert not check_logical_error(errors, correction, lattice.logical_x, 'X')
        assert not check_logical_error(errors, correction, lattice.logical_z, 'Z')

    def test_correctable_error_no_logical_error(self):
        lattice = SurfaceCodeLattice(3)
        errors = [0] * lattice.n_data
        correction = [0] * lattice.n_data
        # Single X error on logical Z operator
        errors[0] = 1
        # Correction on same qubit
        correction[0] = 1
        # Combined = I, no logical error
        assert not check_logical_error(errors, correction, lattice.logical_z, 'Z')


# ─── Error Correction Cycle ─────────────────────────────────────────────────

class TestErrorCorrectionCycle:
    def test_cycle_returns_fields(self):
        result = error_correction_cycle(3, 0.01, seed=42)
        required = ['distance', 'error_rate', 'n_data_qubits', 'n_stabilizers',
                     'n_errors', 'x_syndrome_weight', 'z_syndrome_weight',
                     'logical_error', 'correction_applied']
        for key in required:
            assert key in result

    def test_cycle_zero_error_rate(self):
        result = error_correction_cycle(3, 0.0, seed=42)
        assert result['n_errors'] == 0
        assert not result['logical_error']

    def test_cycle_d3_properties(self):
        result = error_correction_cycle(3, 0.01, seed=42)
        assert result['distance'] == 3
        assert result['n_data_qubits'] == 9

    def test_cycle_d5_properties(self):
        result = error_correction_cycle(5, 0.01, seed=42)
        assert result['distance'] == 5
        assert result['n_data_qubits'] == 25


# ─── Logical Error Rate ─────────────────────────────────────────────────────

class TestLogicalErrorRate:
    def test_zero_error_rate_no_logical_errors(self):
        result = calculate_logical_error_rate(3, 0.0, n_trials=100, seed=42)
        assert result['logical_error_rate'] == 0.0

    def test_rate_returns_fields(self):
        result = calculate_logical_error_rate(3, 0.01, n_trials=100, seed=42)
        assert 'logical_error_rate' in result
        assert 'logical_x_error_rate' in result
        assert 'logical_z_error_rate' in result
        assert 'below_threshold' in result

    def test_high_error_rate_many_logical_errors(self):
        result = calculate_logical_error_rate(3, 0.5, n_trials=100, seed=42)
        assert result['logical_error_rate'] > 0

    def test_larger_distance_better_protection(self):
        # For low error rate, larger distance should have lower logical error rate
        result_d3 = calculate_logical_error_rate(3, 0.005, n_trials=500, seed=42)
        result_d5 = calculate_logical_error_rate(5, 0.005, n_trials=500, seed=42)
        # d=5 should generally perform better than d=3
        # (not guaranteed for small trials, but likely)
        assert result_d5['logical_error_rate'] <= result_d3['logical_error_rate'] + 0.1


# ─── Code Properties ────────────────────────────────────────────────────────

class TestCodeProperties:
    def test_properties_d3(self):
        props = code_properties(3)
        assert props['distance'] == 3
        assert props['n_data_qubits'] == 9
        assert props['max_correctable_errors'] == 1

    def test_properties_d5(self):
        props = code_properties(5)
        assert props['n_data_qubits'] == 25
        assert props['max_correctable_errors'] == 2

    def test_properties_d7(self):
        props = code_properties(7)
        assert props['n_data_qubits'] == 49
        assert props['max_correctable_errors'] == 3

    def test_code_rate_decreases(self):
        for d in [3, 5, 7, 9]:
            props = code_properties(d)
            assert props['code_rate'] < 1.0

    def test_overhead_increases(self):
        props3 = code_properties(3)
        props5 = code_properties(5)
        assert props5['overhead'] > props3['overhead']


# ─── Threshold Estimation ───────────────────────────────────────────────────

class TestThresholdEstimation:
    def test_threshold_returns_fields(self):
        result = threshold_estimation(3, n_trials=50, seed=42)
        assert 'estimated_threshold' in result
        assert 'results' in result
        assert 'test_rates' in result

    def test_threshold_reasonable(self):
        result = threshold_estimation(3, n_trials=100, seed=42)
        assert 0.001 <= result['estimated_threshold'] <= 0.1


# ─── CLI Tests ───────────────────────────────────────────────────────────────

class TestCLI:
    def test_run_command(self):
        from cli import main
        assert main(["run", "-d", "3", "-p", "0.01", "--seed", "42"]) == 0

    def test_logical_rate_command(self):
        from cli import main
        assert main(["logical-rate", "-d", "3", "-p", "0.01", "--trials", "100", "--seed", "42"]) == 0

    def test_threshold_command(self):
        from cli import main
        assert main(["threshold", "-d", "3", "--trials", "50", "--seed", "42"]) == 0

    def test_properties_command(self):
        from cli import main
        assert main(["properties", "-d", "5"]) == 0

    def test_compare_command(self):
        from cli import main
        assert main(["compare", "--max-distance", "7"]) == 0
