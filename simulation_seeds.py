"""Deterministic simulator starts whose per-shot seed ranges can be audited."""

import hashlib


def aer_seed(run_seed, basis):
    """Spread run/basis starts over a JSON-safe 52-bit integer space."""
    if basis not in ("XX", "YY", "ZZ"):
        raise ValueError(f"Unsupported basis: {basis}")
    label = f"qccr-aer-v1:{int(run_seed)}:{basis}".encode("ascii")
    # Aer starts noisy shot j at circuit_seed+j. Widely separated starts
    # give each reported run its own audited range of trajectory seeds.
    return int.from_bytes(hashlib.sha256(label).digest()[:8], "big") & ((1 << 52) - 1)
