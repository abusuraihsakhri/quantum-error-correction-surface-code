# Quantum Error Correction — Rotated Surface Code

Python simulation of a planar rotated surface code with independent depolarizing **data-qubit** noise, ideal stabilizer measurements, and a syndrome-graph decoder. Includes a command-line interface, an in-browser application, a local FastAPI service, and a separate legacy rule-based audit subsystem.

## Browser application

The static application lives in `web/` and runs the **same Python simulation engine** inside the browser through Pyodide. GitHub Pages deployment is configured through `.github/workflows/pages.yml`; availability depends on successful GitHub Pages deployment.

Select a code distance, physical error probability, and seed, then run a single correction cycle or Monte Carlo logical-error-rate study. Results are calculated locally; they are not fabricated or fetched from a hosted API.

**Privacy:** Input parameters and simulation outputs are processed in your browser. The Pyodide runtime is downloaded from jsDelivr on first use. The Python API and audit subsystem, when used separately, run on the server and may retain data in process memory.

## Scientific scope and limitations

- Rotated planar `[[d², 1, d]]` construction: `d²` data qubits and `(d²−1)/2` checks of each Pauli type, including weight-two boundary checks.
- Independent depolarizing channel: on each data qubit, `I` with probability `1−p`, and each of `X`, `Y`, `Z` with probability `p/3`.
- Syndrome extraction assumes **perfect, noiseless stabilizer measurements**. Repeated rounds, faulty gates, correlated noise, leakage, and space-time matching are **not** modeled.
- Decoder uses shortest paths in the syndrome graph, exact defect/boundary minimum-weight matching for at most **18 defects per syndrome type**, and an explicitly identified greedy approximation for larger syndromes. It is **not a Blossom implementation**.
- The Monte Carlo logical-error rate is a sampled failure fraction for this idealized error model. A single-distance scan **cannot estimate a surface-code threshold**. A threshold study requires code-distance crossings and uncertainty quantification.

Use the reported logical rates as illustrative numerical results rather than hardware-performance predictions.

## Installation

Python 3.9 or later:

```bash
git clone https://github.com/abusuraihsakhri/quantum-error-correction-surface-code.git
cd quantum-error-correction-surface-code
python -m pip install -e ".[dev]"
python -m pytest -q
```

The simulation engine itself uses Python's standard library. Pydantic supports the separate agent interface; FastAPI and Uvicorn are optional server dependencies.

## CLI

```bash
quantum-error-correction-surface-code run -d 3 -p 0.01 --seed 42
quantum-error-correction-surface-code logical-rate -d 5 -p 0.01 --trials 200 --seed 42
quantum-error-correction-surface-code properties -d 7
quantum-error-correction-surface-code compare --max-distance 9
quantum-error-correction-surface-code threshold -d 3 --trials 100
```

The `threshold` command prints a fixed-distance suppression scan; **no threshold estimate** is returned. For agent and audit features, use `quantum-qec-audit --help` or `python -m surface_code_qec.cli --help`.

## Local web application and API

```bash
python -m pip install -e ".[web]"
python -m surface_code_qec.cli serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` for the browser interface. The server exposes `GET /health`, `GET /api/qec/properties/{distance}`, `POST /api/qec/cycle`, and `POST /api/qec/rate`. The legacy agent audit endpoints `POST /api/audit` and `POST /api/chat` remain available.

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/qec/cycle \
  -H 'Content-Type: application/json' \
  -d '{"distance":3,"error_rate":0.01,"seed":42}'
```

Docker users can build with `docker build -t surface-qec .` and run with `docker run --rm -p 8000:8000 surface-qec`. Docker Compose requires the `AUDIT_SECRET_KEY` environment variable; generate it with `python -c "import secrets; print(secrets.token_hex(32))"`. The HMAC ledger is process-local, not a persistent audit storage service.

## Testing and deployment

`python -m pytest -q` tests stabilizer commutation, single-qubit correction, random syndrome clearance, deterministic simulation, API routes, and audit HMAC tampering. GitHub Actions tests Python 3.9–3.12, checks Python compilation and JavaScript syntax, and publishes static Pages assets on pushes to `master` when Pages is configured for GitHub Actions.

For the standalone static site, `index.html`, `worker.js`, and `engine.py` must be served together from the same directory. Browser support requires modern Web Worker support and network access to the Pyodide CDN for the first load. The worker performs calculations off the UI thread.

## License

MIT — see [LICENSE](LICENSE).
