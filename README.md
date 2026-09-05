# Quantum Error Correction Surface Code

> **Domain:** Quantum Computing & Error Correction
> **Reference:** Surface Code (Kitaev, 1997; Dennis et al., 2002)

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg?logo=python&logoColor=white)

</div>

---

## Overview

Surface Code Quantum Error Correction — a real QEC simulation engine implementing rotated surface codes with depolarizing noise models, syndrome extraction, and minimum weight perfect matching (MWPM) decoding.

This project provides:
- **Core QEC Engine**: Surface code lattice construction, noise simulation, and error correction cycles
- **CLI Interface**: Command-line tools for running simulations and analyzing code properties
- **Agent System**: Multi-agent coordination with PHI guarding and HMAC-SHA256 audit trails
- **FastAPI Server**: REST API for remote QEC operations

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/quantum-error-correction-surface-code.git
cd quantum-error-correction-surface-code

# Install core dependencies
pip install -e .

# Install with web server support
pip install -e ".[web]"

# Install with development dependencies
pip install -e ".[dev]"
```

---

## Usage

### QEC Simulation CLI

```bash
# Run a single error correction cycle
python cli.py run -d 3 -p 0.01 --seed 42

# Calculate logical error rate
python cli.py logical-rate -d 3 -p 0.01 --trials 1000

# Estimate threshold error rate
python cli.py threshold -d 3 --trials 500

# Show code properties
python cli.py properties -d 5

# Compare different code distances
python cli.py compare --max-distance 11
```

### Agent System CLI

```bash
# Run a single audit task
python -m surface_code_qec.cli audit --task-id TASK-001 --primary 29.4

# Chat with the supervisor
python -m surface_code_qec.cli chat "What is the system status?"

# Verify audit trail integrity
python -m surface_code_qec.cli verify-audit

# Batch process CSV records
python -m surface_code_qec.cli batch -i sample.csv -o results.csv

# Launch FastAPI server
python -m surface_code_qec.cli serve --host 127.0.0.1 --port 8000
```

### FastAPI REST API

```bash
# Start the server
python -m surface_code_qec.cli serve

# Check health
curl http://localhost:8000/health

# Process a task
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{"task_id": "TASK-001", "primary_metric": 29.4, "is_critical_flag": true}'
```

---

## Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest -v --cov=surface_code_qec --cov=agents
```

---

## Project Structure

```
quantum-error-correction-surface-code/
├── surface_code_qec/          # Core QEC package
│   ├── engine.py              # Surface code engine & agent integration
│   ├── models.py              # Data models & telemetry definitions
│   ├── agents.py              # Multi-agent coordination system
│   ├── cli.py                 # Package CLI interface
│   └── server.py              # FastAPI REST server
├── agents/                    # Enterprise agent system
│   ├── base.py                # PHI guard, audit trail, security
│   ├── models.py              # Pydantic schemas
│   ├── workers.py             # Domain worker agents
│   ├── supervisor.py          # Supervisor orchestrator
│   ├── api.py                 # FastAPI application
│   ├── metrics.py             # Prometheus metrics
│   ├── learning.py            # Active learning engine
│   ├── llm_factory.py         # LLM provider factory
│   └── streamer.py            # WebSocket telemetry
├── cli.py                     # QEC simulation CLI entry point
├── tests/                     # Test suite
│   ├── test_surface_code_qec.py
│   ├── test_quantum_error_correction_surface_code.py
│   └── test_enrichment.py
├── web/index.html             # Operations console UI
├── enrichment.py              # Enrichment feature modules
├── pyproject.toml             # Project configuration
├── Dockerfile                 # Container build
└── docker-compose.yml         # Container deployment
```

---

## Surface Code Parameters

| Parameter | Description |
|:----------|:------------|
| `distance` | Code distance (odd integer, >= 3) |
| `error_rate` | Physical error rate (0.0 to 1.0) |
| `trials` | Number of simulation trials |
| `seed` | Random seed for reproducibility |

---

## Security

- **Audit Trail**: HMAC-SHA256 tamper-evident logging for all operations
- **PHI Guard**: Zero-PHI outbound interceptor blocking sensitive identifiers
- **Input Validation**: Bounds checking on all simulation parameters

Set `AUDIT_SECRET_KEY` environment variable in production:
```bash
export AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

---

## Docker Deployment

```bash
# Build and run
docker-compose up --build

# Or manually
docker build -t quantum-error-correction-surface-code .
docker run -p 8000:8000 quantum-error-correction-surface-code
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.
