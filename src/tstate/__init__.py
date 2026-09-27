"""tstate — explicit-state reachability and attractor computation."""

from tstate.core import (
    TransitionSystem,
    from_count_vector,
    make_quotient_system,
    make_system,
    to_count_vector,
)

__version__ = "0.1.0"
__all__ = [
    "TransitionSystem",
    "from_count_vector",
    "make_quotient_system",
    "make_system",
    "to_count_vector",
    "__version__",
]
