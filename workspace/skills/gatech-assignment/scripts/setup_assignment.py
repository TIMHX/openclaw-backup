#!/usr/bin/env python3
"""
GaTech Assignment Setup Script
Creates directory structure for GaTech assignments.
"""

import argparse
from pathlib import Path


def create_assignment_structure(base_dir="assignment_work"):
    """Create standard assignment directory structure."""
    dirs = [
        f"{base_dir}/data",
        f"{base_dir}/data/raw",
        f"{base_dir}/data/processed",
        f"{base_dir}/scripts",
        f"{base_dir}/output",
        f"{base_dir}/output/plots",
        f"{base_dir}/output/tables",
        f"{base_dir}/notebooks",
    ]

    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"Created: {d}")

    return base_dir


def main():
    parser = argparse.ArgumentParser(description="Setup GaTech assignment workspace")
    parser.add_argument("--dir", "-d", default="assignment_work", help="Base directory")

    args = parser.parse_args()

    create_assignment_structure(args.dir)

    print(f"\nAssignment workspace created at: {args.dir}/")
    print("Next steps:")
    print(f"  1. Check for data files in repo (follow assignment instructions)")
    print(f"  2. Create analysis scripts in {args.dir}/scripts/")
    print(f"  3. Run analyses and save outputs to {args.dir}/output/")


if __name__ == "__main__":
    main()
