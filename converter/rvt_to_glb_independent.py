import sys
import subprocess
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REVITER_DIR = Path.home() / "Documents" / "reviter"
OUTPUT_DIR = PROJECT_ROOT / "output"


def convert_rvt_to_glb(input_file):
    source = Path(input_file).resolve()

    # Validate input file
    if not source.is_file():
        raise FileNotFoundError(f"RVT file not found: {source}")

    if source.suffix.lower() != ".rvt":
        raise ValueError("Input must be an .rvt file")

    # Validate Reviter installation
    if not (REVITER_DIR / "package.json").is_file():
        raise FileNotFoundError(
            f"Reviter repository not found: {REVITER_DIR}"
        )

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT_DIR / f"{source.stem}.glb"

    # Build Windows command
    command = (
        f'npm run extract -- "{source}" '
        f'--out "{destination}"'
    )

    print("=" * 50)
    print("RVT → GLB Independent Converter")
    print("=" * 50)
    print(f"Input:  {source}")
    print(f"Output: {destination}")
    print("Method: Local Reviter conversion")
    print("Autodesk APS: Not used")
    print("\nStarting conversion...\n")

    # Run Reviter locally
    result = subprocess.run(
        command,
        cwd=str(REVITER_DIR),
        text=True,
        shell=True
    )

    # Check conversion result
    if result.returncode != 0:
        raise RuntimeError(
            f"Reviter conversion failed "
            f"(exit code {result.returncode})"
        )

    # Verify output
    if not destination.is_file():
        raise RuntimeError(
            "Conversion finished, but the GLB file was not created."
        )

    if destination.stat().st_size == 0:
        raise RuntimeError("The generated GLB file is empty.")

    size_mb = destination.stat().st_size / (1024 * 1024)

    print("\n" + "=" * 50)
    print("CONVERSION SUCCESSFUL")
    print("=" * 50)
    print(f"GLB file: {destination}")
    print(f"File size: {size_mb:.2f} MB")

    return destination


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            'Usage: python converter\\rvt_to_glb_independent.py '
            '"input\\model.rvt"'
        )
        sys.exit(1)

    try:
        convert_rvt_to_glb(sys.argv[1])

    except Exception as error:
        print(f"\nERROR: {error}")
        sys.exit(1)