import os
import sys
import subprocess
import tempfile


BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"


def convert_fbx_to_glb(fbx_path, glb_path):

    print("=" * 60)
    print("FBX → GLB Converter")
    print("=" * 60)

    print(f"Input : {fbx_path}")
    print(f"Output: {glb_path}")
    print()

    # ---------------------------------------------------------
    # Check files
    # ---------------------------------------------------------

    if not os.path.exists(fbx_path):
        raise FileNotFoundError(
            f"FBX file not found: {fbx_path}"
        )

    if not os.path.exists(BLENDER_PATH):
        raise FileNotFoundError(
            f"Blender not found: {BLENDER_PATH}"
        )

    # ---------------------------------------------------------
    # Create temporary Blender Python script
    # ---------------------------------------------------------

    blender_script = r'''
import bpy
import sys

# Get arguments after "--"
args = sys.argv

if "--" not in args:
    raise RuntimeError("No input/output arguments supplied.")

args = args[args.index("--") + 1:]

fbx_path = args[0]
glb_path = args[1]

print("Blender FBX importer starting...")
print("Input FBX:", fbx_path)
print("Output GLB:", glb_path)

# Clear default scene
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Import FBX
print("Importing FBX...")

bpy.ops.import_scene.fbx(
    filepath=fbx_path
)

print("FBX imported successfully.")

# Select all objects
bpy.ops.object.select_all(action="SELECT")

# Export GLB
print("Exporting GLB...")

bpy.ops.export_scene.gltf(
    filepath=glb_path,
    export_format="GLB",
    use_selection=True
)

print("GLB export completed.")
'''

    # ---------------------------------------------------------
    # Write temporary script
    # ---------------------------------------------------------

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8"
    ) as temp_file:

        temp_file.write(blender_script)

        script_path = temp_file.name

    try:

        # -----------------------------------------------------
        # Run Blender in background mode
        # -----------------------------------------------------

        command = [
            BLENDER_PATH,
            "--background",
            "--python",
            script_path,
            "--",
            os.path.abspath(fbx_path),
            os.path.abspath(glb_path)
        ]

        print("Starting Blender...")
        print()

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        # Show Blender output
        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print(result.stderr)

        # -----------------------------------------------------
        # Check Blender result
        # -----------------------------------------------------

        if result.returncode != 0:

            raise RuntimeError(
                f"Blender conversion failed "
                f"with exit code {result.returncode}"
            )

        # -----------------------------------------------------
        # Check GLB
        # -----------------------------------------------------

        if not os.path.exists(glb_path):

            raise RuntimeError(
                "Blender finished, but the GLB file "
                "was not created."
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

    finally:

        # Remove temporary Blender script
        if os.path.exists(script_path):
            os.remove(script_path)


# =============================================================
# Command-line usage
# =============================================================

if __name__ == "__main__":

    if len(sys.argv) < 2:

        print(
            "Usage:\n"
            "python converter\\fbx_to_glb.py "
            "input\\model.fbx"
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

    convert_fbx_to_glb(
        input_file,
        output_file
    )