"""
Available services for testing.

Add your own functions here. Each function should:
- Accept parsed arguments
- Return a result that can be compared to expected output
"""


def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


def concat(*args: str) -> str:
    """Concatenate strings."""
    return "".join(args)


# Registry of available services
SERVICES = {
    "add": add,
    "subtract": subtract,
    "multiply": multiply,
    "concat": concat,
}


def get_service(name: str):
    """Get a service function by name."""
    if name not in SERVICES:
        raise ValueError(f"Unknown service: {name}. Available: {list(SERVICES.keys())}")
    return SERVICES[name]
