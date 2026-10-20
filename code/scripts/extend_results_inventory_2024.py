"""Compatibility entry point for building the current results inventory.

The former extension workflow appended 2024 values to a superseded inventory.
The current builder writes one canonical inventory directly.
"""

from build_results_inventory import main


if __name__ == "__main__":
    main()
