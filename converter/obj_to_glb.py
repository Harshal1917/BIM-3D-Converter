import os
import sys
import trimesh


def convert_obj_to_glb(obj_path, glb_path):
    print("=" * 60)
    print("OBJ → GLB Converter")
    print("=" * 60)

    print(f"Input : {obj_path}")
    print(f"Output: {glb_path}")
    print()

    # Check input
    if not os.path.exists(obj_path):
        raise FileNotFoundError(
            f"OBJ file not found: {obj_path}"
        )

    print("Loading OBJ file...")

    # Load OBJ
    loaded = trimesh.load(
        obj_path,
        force="scene"
    )

    print("OBJ loaded successfully.")

    # Make sure we have a Scene
    if isinstance(loaded, trimesh.Trimesh):
        scene = trimesh.Scene(loaded)
    else:
        scene = loaded

    print(f"Objects found: {len(scene.geometry)}")

    # Check geometry
    if len(scene.geometry) == 0:
        raise RuntimeError(
            "No geometry found in OBJ file."
        )

    # Create output directory
    output_directory = os.path.dirname(glb_path)

    if output_directory:
        os.makedirs(
            output_directory,
            exist_ok=True
        )

    print("Exporting GLB...")

    # Export GLB
    scene.export(
        glb_path,
        file_type="glb"
    )

    # Check result
    if not os.path.exists(glb_path):
        raise RuntimeError(
            "GLB file was not created."
        )

    file_size = os.path.getsize(glb_path)

    print()
    print("=" * 60)
    print("CONVERSION COMPLETE")
    print("=" * 60)

    print(f"GLB created: {glb_path}")
    print(
        f"GLB size   : "
        f"{file_size / (1024 * 1024):.2f} MB"
    )


if __name__ == "__main__":

    if len(sys.argv) < 2:

        print(
            "Usage:\n"
            "python converter\\obj_to_glb.py "
            "input\\model.obj"
        )

        sys.exit(1)

    input_file = sys.argv[1]

    # Automatically create output filename
    filename = os.path.splitext(
        os.path.basename(input_file)
    )[0]

    output_file = os.path.join(
        "output",
        filename + ".glb"
    )

    convert_obj_to_glb(
        input_file,
        output_file
    )