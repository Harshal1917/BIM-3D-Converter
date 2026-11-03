import os
import sys
import ifcopenshell
import ifcopenshell.geom
import trimesh


def convert_ifc_to_glb(ifc_path, glb_path):
    print("=" * 60)
    print("IFC → GLB Converter")
    print("=" * 60)

    print(f"Input : {ifc_path}")
    print(f"Output: {glb_path}")
    print()

    # ---------------------------------------------------------
    # Check input
    # ---------------------------------------------------------

    if not os.path.exists(ifc_path):
        raise FileNotFoundError(f"IFC file not found: {ifc_path}")

    # ---------------------------------------------------------
    # Open IFC
    # ---------------------------------------------------------

    print("Opening IFC file...")

    model = ifcopenshell.open(ifc_path)

    print(f"IFC opened successfully.")
    print(f"Schema: {model.schema}")

    # ---------------------------------------------------------
    # Geometry settings
    # ---------------------------------------------------------

    settings = ifcopenshell.geom.settings()

    settings.set(
        settings.USE_WORLD_COORDS,
        True
    )

    # ---------------------------------------------------------
    # Find IFC products with geometry
    # ---------------------------------------------------------

    products = model.by_type("IfcProduct")

    print(f"IFC products found: {len(products)}")
    print()

    meshes = []

    # ---------------------------------------------------------
    # Convert IFC geometry
    # ---------------------------------------------------------

    for index, product in enumerate(products, start=1):

        try:

            shape = ifcopenshell.geom.create_shape(
                settings,
                product
            )

            geometry = shape.geometry

            vertices = geometry.verts
            faces = geometry.faces

            # Convert vertex list to XYZ coordinates
            vertices = [
                (
                    vertices[i],
                    vertices[i + 1],
                    vertices[i + 2]
                )
                for i in range(0, len(vertices), 3)
            ]

            # Convert triangle indices
            faces = [
                (
                    faces[i],
                    faces[i + 1],
                    faces[i + 2]
                )
                for i in range(0, len(faces), 3)
            ]

            if len(vertices) == 0 or len(faces) == 0:
                continue

            mesh = trimesh.Trimesh(
                vertices=vertices,
                faces=faces,
                process=False
            )

            meshes.append(mesh)

            print(
                f"[{index}/{len(products)}] "
                f"{product.is_a()} "
                f"→ {len(vertices)} vertices, "
                f"{len(faces)} triangles"
            )

        except Exception as error:

            print(
                f"[{index}/{len(products)}] "
                f"Skipped {product.is_a()}: {error}"
            )

    # ---------------------------------------------------------
    # Check result
    # ---------------------------------------------------------

    if not meshes:
        raise RuntimeError(
            "No geometry was successfully extracted from the IFC file."
        )

    print()
    print(f"Meshes generated: {len(meshes)}")

    # ---------------------------------------------------------
    # Create scene
    # ---------------------------------------------------------

    print("Creating GLB scene...")

    scene = trimesh.Scene()

    for index, mesh in enumerate(meshes):

        scene.add_geometry(
            mesh,
            node_name=f"IFC_Object_{index}"
        )

    # ---------------------------------------------------------
    # Create output directory
    # ---------------------------------------------------------

    output_directory = os.path.dirname(glb_path)

    if output_directory:
        os.makedirs(
            output_directory,
            exist_ok=True
        )

    # ---------------------------------------------------------
    # Export GLB
    # ---------------------------------------------------------

    print("Exporting GLB...")

    scene.export(
        glb_path,
        file_type="glb"
    )

    # ---------------------------------------------------------
    # Finished
    # ---------------------------------------------------------

    file_size = os.path.getsize(glb_path)

    print()
    print("=" * 60)
    print("CONVERSION COMPLETE")
    print("=" * 60)

    print(f"GLB created: {glb_path}")
    print(f"GLB size   : {file_size / (1024 * 1024):.2f} MB")
    print()


# =============================================================
# Command-line usage
# =============================================================

if __name__ == "__main__":

    if len(sys.argv) < 2:

        print(
            "Usage:\n"
            "python converter\\ifc_to_glb.py "
            "input\\model.ifc"
        )

        sys.exit(1)

    input_file = sys.argv[1]

    # Generate output filename automatically
    filename = os.path.splitext(
        os.path.basename(input_file)
    )[0]

    output_file = os.path.join(
        "output",
        filename + ".glb"
    )

    convert_ifc_to_glb(
        input_file,
        output_file
    )