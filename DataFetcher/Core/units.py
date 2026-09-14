"""
MamyFlux (MF) unit handling, per https://industrialist.miraheze.org/wiki/MamyFlux

    Name          Unit   Equivalence in MF
    MamyFlux      MF     1
    KiloMamyFlux  kMF    1,000
    MegaMamyFlux  MMF    1,000,000
    GigaMamyFlux  GMF    1,000,000,000
    TeraMamyFlux  TMF    1,000,000,000,000
    PetaMamyFlux  PMF    1,000,000,000,000,000

Rates (recipe power draw, machine power input/output) are "MF/s"; stored capacities (machine buffer size) are just "MF". Both use the
same prefix scale, so one parser covers both. The trailing "/s" is optional in the regex and just isn't present for capacity values.
"""

from __future__ import annotations
import re

SCALE = {
    None: 1,
    "k": 1_000,
    "M": 1_000_000,
    "G": 1_000_000_000,
    "T": 1_000_000_000_000,
    "P": 1_000_000_000_000_000,
}

# e.g. "⚡3kMF/s", "100kMF/s", "17.9kMF/s", "⚡50kMF" (no /s), "1.2PMF/s"
POWER_RE = re.compile(r"([\d.]+)\s*([kMGTP])?MF(/s)?")


def parse_power(text: str) -> tuple[str, float | None]:
    """Returns (raw_text, value_in_base_MF_units). value is None if no match."""
    m = POWER_RE.search(text)

    if not m:
        return text, None
        
    magnitude, scale, _ = m.groups()
    return text, float(magnitude) * SCALE[scale]
