"""
CLI for Surface Code Quantum Error Correction Engine.
Provides commands for error correction simulation, threshold estimation, and code analysis.
"""
import argparse
import sys

from surface_code_qec.engine import (
    SurfaceCodeLattice, error_correction_cycle,
    calculate_logical_error_rate, threshold_estimation,
    code_properties, apply_depolarizing_noise,
    extract_syndrome, syndrome_to_defects,
)


def cmd_run(args):
    """Run a single error correction cycle."""
    result = error_correction_cycle(args.distance, args.error_rate, seed=args.seed)
    
    print(f"Surface Code Error Correction Cycle:")
    print(f"  Code distance:       d = {result['distance']}")
    print(f"  Physical error rate:   {result['error_rate']:.4f}")
    print(f"  Data qubits:           {result['n_data_qubits']}")
    print(f"  Stabilizers:           {result['n_stabilizers']}")
    print(f"  Errors injected:       {result['n_errors']}")
    print(f"  X-syndrome weight:     {result['x_syndrome_weight']}")
    print(f"  Z-syndrome weight:     {result['z_syndrome_weight']}")
    print(f"  X-defects:             {result['x_defects']}")
    print(f"  Z-defects:             {result['z_defects']}")
    print(f"  X-matches:             {result['x_matches']}")
    print(f"  Z-matches:             {result['z_matches']}")
    print(f"  Correction applied:    {result['correction_applied']}")
    print(f"  Logical X error:       {result['logical_x_error']}")
    print(f"  Logical Z error:       {result['logical_z_error']}")
    print(f"  Logical error:         {result['logical_error']}")
    return 0


def cmd_logical_rate(args):
    """Calculate logical error rate."""
    result = calculate_logical_error_rate(
        args.distance, args.error_rate,
        n_trials=args.trials, seed=args.seed,
    )
    
    print(f"Logical Error Rate (d={result['distance']}, p={result['physical_error_rate']:.4f}):")
    print(f"  Trials:                {result['n_trials']}")
    print(f"  Logical error rate:    {result['logical_error_rate']:.6f}")
    print(f"  Logical X error rate:  {result['logical_x_error_rate']:.6f}")
    print(f"  Logical Z error rate:  {result['logical_z_error_rate']:.6f}")
    print(f"  Below threshold:       {result['below_threshold']}")
    print(f"  Suppression factor:    {result['suppression_factor']:.2f}x")
    return 0


def cmd_threshold(args):
    """Estimate threshold error rate."""
    result = threshold_estimation(
        args.distance, n_trials=args.trials, seed=args.seed,
    )
    
    print(f"Threshold Estimation (d={result['distance']}):")
    print(f"  Trials per rate:       {result['n_trials_per_rate']}")
    print(f"  Estimated threshold:   {result['estimated_threshold']:.4f}")
    print(f"\n  {'Physical Rate':>15s} {'Logical Rate':>15s} {'Below Threshold':>15s}")
    print(f"  {'-'*45}")
    for r in result['results']:
        below = "✓" if r['below_threshold'] else "✗"
        print(f"  {r['physical_error_rate']:15.4f} {r['logical_error_rate']:15.6f} {below:>15s}")
    return 0


def cmd_properties(args):
    """Show code properties."""
    result = code_properties(args.distance)
    
    print(f"Surface Code Properties (d={result['distance']}):")
    print(f"  Data qubits:           {result['n_data_qubits']}")
    print(f"  Stabilizers:           {result['n_stabilizers']}")
    print(f"  Max correctable:       {result['max_correctable_errors']} errors")
    print(f"  Code rate:             {result['code_rate']:.4f}")
    print(f"  Overhead:              {result['overhead']}x")
    print(f"  Threshold estimate:    {result['threshold_estimate']:.2%}")
    return 0


def cmd_compare(args):
    """Compare different code distances."""
    print(f"Surface Code Distance Comparison:")
    print(f"  {'Distance':>8s} {'Qubits':>8s} {'Corrects':>10s} {'Rate':>8s} {'Overhead':>10s}")
    print(f"  {'-'*50}")
    for d in range(3, args.max_distance + 1, 2):
        result = code_properties(d)
        print(f"  {result['distance']:8d} {result['n_data_qubits']:8d} "
              f"{result['max_correctable_errors']:10d} "
              f"{result['code_rate']:8.4f} {result['overhead']:10d}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="quantum-error-correction-surface-code",
        description="Surface Code Quantum Error Correction — real QEC simulation"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p = sub.add_parser("run", help="Run single error correction cycle")
    p.add_argument("-d", "--distance", type=int, default=3, help="Code distance (odd, >=3)")
    p.add_argument("-p", "--error-rate", type=float, default=0.01, help="Physical error rate")
    p.add_argument("--seed", type=int, default=42, help="Random seed")

    # logical-rate
    p = sub.add_parser("logical-rate", help="Calculate logical error rate")
    p.add_argument("-d", "--distance", type=int, default=3, help="Code distance")
    p.add_argument("-p", "--error-rate", type=float, default=0.01, help="Physical error rate")
    p.add_argument("--trials", type=int, default=1000, help="Number of trials")
    p.add_argument("--seed", type=int, default=42, help="Random seed")

    # threshold
    p = sub.add_parser("threshold", help="Estimate threshold error rate")
    p.add_argument("-d", "--distance", type=int, default=3, help="Code distance")
    p.add_argument("--trials", type=int, default=500, help="Trials per error rate")
    p.add_argument("--seed", type=int, default=42, help="Random seed")

    # properties
    p = sub.add_parser("properties", help="Show code properties")
    p.add_argument("-d", "--distance", type=int, default=3, help="Code distance")

    # compare
    p = sub.add_parser("compare", help="Compare different distances")
    p.add_argument("--max-distance", type=int, default=11, help="Maximum distance to show")

    args = parser.parse_args(argv)
    handlers = {
        'run': cmd_run,
        'logical-rate': cmd_logical_rate,
        'threshold': cmd_threshold,
        'properties': cmd_properties,
        'compare': cmd_compare,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
