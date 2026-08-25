# Surface Code Quantum Error Correction

Real implementation of surface code QEC (Kitaev, 1997) using Python stdlib only.

## What This Actually Does

- **Surface code lattice** — d×d grid of data qubits with X and Z stabilizers
- **X-stabilizers** — detect Z errors (bit flips) on face qubits
- **Z-stabilizers** — detect X errors (phase flips) on vertex qubits
- **Syndrome extraction** — measure stabilizers to detect errors
- **Minimum weight perfect matching** — simplified decoder pairing defects
- **Logical error rate calculation** — Monte Carlo estimation
- **Code distance d** — corrects up to (d-1)/2 errors
- **Threshold estimation** — ~1% for independent depolarizing noise

### Code Properties

| Distance | Data Qubits | Corrects | Rate |
|:---:|:---:|:---:|:---:|
| 3 | 9 | 1 | 0.111 |
| 5 | 25 | 2 | 0.040 |
| 7 | 49 | 3 | 0.020 |
| 9 | 81 | 4 | 0.012 |

## Usage

```bash
# Run single error correction cycle
python cli.py run -d 3 -p 0.01 --seed 42

# Calculate logical error rate
python cli.py logical-rate -d 3 -p 0.01 --trials 1000

# Estimate threshold
python cli.py threshold -d 3 --trials 500

# Show code properties
python cli.py properties -d 5

# Compare distances
python cli.py compare --max-distance 11
```

## API

```python
from surface_code_qec.engine import (
    SurfaceCodeLattice, error_correction_cycle,
    calculate_logical_error_rate, threshold_estimation,
)

# Single cycle
result = error_correction_cycle(distance=3, error_rate=0.01, seed=42)
print(f"Logical error: {result['logical_error']}")

# Logical error rate
rate = calculate_logical_error_rate(distance=3, error_rate=0.01, n_trials=1000)
print(f"Logical error rate: {rate['logical_error_rate']}")
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Limitations

- Simplified matching decoder (not full MWPM)
- Independent depolarizing noise only
- No correlated errors or leakage
- Small code distances practical (d ≤ ~15)
