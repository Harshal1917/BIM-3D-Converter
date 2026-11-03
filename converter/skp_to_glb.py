import sys
from pathlib import Path

from openskp import SkpFile
from openskp.export import glb


def convert_skp_to_glb(input_file, output_file):
    input_path = Path(input_file)
    output_path = Path(output_file)

    print("=" * 50)
    print("SKP → GLB Converter")
    print("=" * 50)

    print(f"Input : {input_path}")
    print(f"Output: {output_path}")

    if not input_path.exists():
        print("ERROR: Input SKP file does not exist.")
        sys.exit(1)

    try:
        print("\nLoading SKP file...")

        skp = SkpFile.open(str(input_path))

        # Parse the SKP file first
        model = skp.parse()

        print("SKP parsed successfully.")
        print(f"SketchUp version: {model.version}")

        print("\nConverting to GLB...")

        # OpenSKP's GLB exporter accepts the SkpFile
        # and internally builds the required scene.
        glb.export(skp, str(output_path))

        if not output_path.exists():
            print("ERROR: GLB file was not created.")
            sys.exit(1)

        size_mb = output_path.stat().st_size / (1024 * 1024)

        print("\nSUCCESS!")
        print(f"GLB created: {output_path}")
        print(f"GLB size: {size_mb:.2f} MB")

    except Exception as e:
        print("\nERROR during conversion:")
        print(e)
        sys.exit(1)


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage:")
        print("python converter\\skp_to_glb.py input\\model.skp")
        sys.exit(1)

    input_file = sys.argv[1]

    output_file = Path("output") / (Path(input_file).stem + ".glb")

    convert_skp_to_glb(input_file, output_file)