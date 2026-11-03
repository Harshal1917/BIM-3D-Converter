import sys
import time
import os
import base64
import json
from pathlib import Path

import requests
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

CLIENT_ID = os.getenv("APS_CLIENT_ID")
CLIENT_SECRET = os.getenv("APS_CLIENT_SECRET")

APS_BASE = "https://developer.api.autodesk.com"

OUTPUT_DIR = Path("output")

BUCKET_KEY = "glbconversionpipeline"


# ============================================================
# CHECK CREDENTIALS
# ============================================================

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: APS_CLIENT_ID / APS_CLIENT_SECRET not found.")
    print()
    print("Create a .env file containing:")
    print("APS_CLIENT_ID=...")
    print("APS_CLIENT_SECRET=...")
    sys.exit(1)


# ============================================================
# RESPONSE CHECK
# ============================================================

def check_response(response, operation):

    if not response.ok:

        print()
        print("=" * 60)
        print(f"ERROR during {operation}")
        print("=" * 60)

        print(f"HTTP status: {response.status_code}")
        print(response.text)

        sys.exit(1)


# ============================================================
# GET APS ACCESS TOKEN
# ============================================================

def get_access_token():

    print("\n[1/7] Getting APS access token...")

    url = f"{APS_BASE}/authentication/v2/token"

    data = {
        "grant_type": "client_credentials",
        "scope": "data:read data:write bucket:create bucket:read"
    }

    response = requests.post(
        url,
        data=data,
        auth=(CLIENT_ID, CLIENT_SECRET)
    )

    check_response(
        response,
        "APS authentication"
    )

    token = response.json()["access_token"]

    print("APS authentication successful.")

    return token


# ============================================================
# CREATE / CHECK BUCKET
# ============================================================

def create_bucket(token):

    print("\n[2/7] Checking APS bucket...")

    url = f"{APS_BASE}/oss/v2/buckets"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "bucketKey": BUCKET_KEY,
        "policyKey": "transient"
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    if response.status_code in (200, 201):

        print("APS bucket created.")

    elif response.status_code == 409:

        print("APS bucket already exists.")

    else:

        check_response(
            response,
            "bucket creation"
        )


# ============================================================
# UPLOAD RVT
# ============================================================
def upload_file(token, file_path):

    print("\n[3/7] Uploading RVT to APS...")

    object_key = file_path.name

    file_size = file_path.stat().st_size

    # --------------------------------------------------------
    # Calculate number of upload parts
    # --------------------------------------------------------

    part_size = 5 * 1024 * 1024  # 5 MB

    parts = max(
        1,
        (file_size + part_size - 1) // part_size
    )

    print(f"File size: {file_size / (1024 * 1024):.2f} MB")
    print(f"Upload parts: {parts}")

    # --------------------------------------------------------
    # APS allows a maximum of 25 signed URLs per request
    # --------------------------------------------------------

    uploaded_parts = 0
    upload_key = None

    with open(file_path, "rb") as file:

        first_part = 1

        while uploaded_parts < parts:

            remaining_parts = parts - uploaded_parts

            requested_parts = min(
                25,
                remaining_parts
            )

            # ------------------------------------------------
            # Get signed S3 upload URLs
            # ------------------------------------------------

            print(
                f"\nRequesting signed upload URLs "
                f"for parts {first_part} - "
                f"{first_part + requested_parts - 1}..."
            )

            url = (
                f"{APS_BASE}/oss/v2/buckets/"
                f"{BUCKET_KEY}/objects/"
                f"{requests.utils.quote(object_key, safe='')}"
                f"/signeds3upload"
            )

            params = {
                "parts": requested_parts,
                "firstPart": first_part
            }

            if upload_key:
                params["uploadKey"] = upload_key

            headers = {
                "Authorization": f"Bearer {token}"
            }

            response = requests.get(
                url,
                headers=headers,
                params=params
            )

            check_response(
                response,
                "getting signed S3 upload URLs"
            )

            upload_info = response.json()

            upload_urls = upload_info["urls"]

            upload_key = upload_info["uploadKey"]

            # ------------------------------------------------
            # Upload each part directly to S3
            # ------------------------------------------------

            for index, upload_url in enumerate(
                upload_urls
            ):

                part_number = first_part + index

                chunk = file.read(
                    part_size
                )

                if not chunk:
                    break

                print(
                    f"Uploading part "
                    f"{part_number}/{parts}..."
                )

                s3_response = requests.put(
                    upload_url,
                    data=chunk
                )

                if not s3_response.ok:

                    print()
                    print(
                        f"ERROR uploading part "
                        f"{part_number}"
                    )

                    print(
                        f"HTTP status: "
                        f"{s3_response.status_code}"
                    )

                    print(
                        s3_response.text
                    )

                    sys.exit(1)

                uploaded_parts += 1

            first_part += len(upload_urls)

    # --------------------------------------------------------
    # Complete the upload
    # --------------------------------------------------------

    print("\nFinalizing APS upload...")

    complete_url = (
        f"{APS_BASE}/oss/v2/buckets/"
        f"{BUCKET_KEY}/objects/"
        f"{requests.utils.quote(object_key, safe='')}"
        f"/signeds3upload"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "uploadKey": upload_key
    }

    response = requests.post(
        complete_url,
        headers=headers,
        json=payload
    )

    check_response(
        response,
        "completing S3 upload"
    )

    object_data = response.json()

    print("RVT uploaded successfully.")

    return object_data

# ============================================================
# CREATE RVT → IFC TRANSLATION JOB
# ============================================================

def create_translation_job(token, object_id):

    print("\n[4/7] Starting RVT → IFC translation...")

    # Convert object ID to URL-safe Base64 URN
    urn = base64.urlsafe_b64encode(
        object_id.encode("utf-8")
    ).decode("utf-8").rstrip("=")

    url = (
        f"{APS_BASE}/modelderivative/v2/"
        f"designdata/job"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-ads-force": "true"
    }

    payload = {
        "input": {
            "urn": urn
        },
        "output": {
            "formats": [
                {
                    "type": "ifc"
                }
            ]
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    check_response(
        response,
        "RVT → IFC translation job"
    )

    print("RVT → IFC translation job submitted.")

    return urn


# ============================================================
# WAIT FOR TRANSLATION
# ============================================================

def wait_for_translation(token, urn):

    print("\n[5/7] Waiting for RVT → IFC translation...")

    encoded_urn = requests.utils.quote(
        urn,
        safe=""
    )

    url = (
        f"{APS_BASE}/modelderivative/v2/"
        f"designdata/{encoded_urn}/manifest"
    )

    headers = {
        "Authorization": f"Bearer {token}"
    }

    for attempt in range(120):

        response = requests.get(
            url,
            headers=headers
        )

        check_response(
            response,
            "translation status"
        )

        manifest = response.json()

        status = manifest.get("status")

        print(
            f"Translation status: {status}"
        )

        if status == "success":

            print(
                "RVT → IFC translation completed."
            )

            return manifest

        if status == "failed":

            print()
            print("APS translation FAILED.")
            print()

            print(
                json.dumps(
                    manifest,
                    indent=2
                )
            )

            sys.exit(1)

        time.sleep(10)

    print()
    print("ERROR: Translation timeout.")
    sys.exit(1)


# ============================================================
# FIND IFC DERIVATIVE
# ============================================================

def find_ifc_derivative(manifest):

    print("\n[6/7] Finding generated IFC file...")

    def search_node(node):

        if not isinstance(node, dict):
            return None

        # Check direct URN
        node_urn = node.get("urn")

        if node_urn:

            text = str(node_urn).lower()

            if text.endswith(".ifc"):

                return node_urn

        # Search children
        children = node.get(
            "children",
            []
        )

        for child in children:

            result = search_node(child)

            if result:
                return result

        # Search derivatives
        derivatives = node.get(
            "derivatives",
            []
        )

        for derivative in derivatives:

            result = search_node(derivative)

            if result:
                return result

        return None

    derivative_urn = search_node(manifest)

    if not derivative_urn:

        print()
        print("ERROR: IFC derivative not found.")
        print()
        print("APS manifest:")
        print(
            json.dumps(
                manifest,
                indent=2
            )
        )

        sys.exit(1)

    print("IFC derivative found.")

    return derivative_urn


# ============================================================
# DOWNLOAD IFC
# ============================================================

def download_derivative(
    token,
    source_urn,
    derivative_urn,
    output_ifc
):

    print("\nDownloading IFC...")

    encoded_source = requests.utils.quote(
        source_urn,
        safe=""
    )

    encoded_derivative = requests.utils.quote(
        derivative_urn,
        safe=""
    )

    url = (
        f"{APS_BASE}/modelderivative/v2/"
        f"designdata/{encoded_source}/"
        f"manifest/{encoded_derivative}/"
        f"signedcookies"
    )

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(
        url,
        headers=headers
    )

    check_response(
        response,
        "getting IFC download URL"
    )

    data = response.json()

    download_url = data["url"]

    # --------------------------------------------------------
    # Extract CloudFront cookies
    # --------------------------------------------------------

    cookies = response.headers.get(
        "Set-Cookie",
        ""
    )

    policy = None
    key_pair_id = None
    signature = None

    for part in cookies.replace(
        ",",
        ";"
    ).split(";"):

        part = part.strip()

        if part.startswith(
            "CloudFront-Policy="
        ):

            policy = part.split(
                "=",
                1
            )[1]

        elif part.startswith(
            "CloudFront-Key-Pair-Id="
        ):

            key_pair_id = part.split(
                "=",
                1
            )[1]

        elif part.startswith(
            "CloudFront-Signature="
        ):

            signature = part.split(
                "=",
                1
            )[1]

    if not policy or not key_pair_id or not signature:

        print()
        print(
            "ERROR: APS download cookies were not returned."
        )

        print(
            response.headers
        )

        sys.exit(1)

    download_url += (
        f"?Policy={policy}"
        f"&Key-Pair-Id={key_pair_id}"
        f"&Signature={signature}"
    )

    # --------------------------------------------------------
    # Download IFC
    # --------------------------------------------------------

    print("Downloading IFC data...")

    response = requests.get(
        download_url,
        stream=True
    )

    if not response.ok:

        print()
        print("ERROR downloading IFC.")
        print(
            f"HTTP status: {response.status_code}"
        )

        sys.exit(1)

    with open(
        output_ifc,
        "wb"
    ) as file:

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):

            if chunk:
                file.write(chunk)

    print(
        f"IFC downloaded: {output_ifc}"
    )


# ============================================================
# IFC → GLB
# ============================================================

def convert_ifc_to_glb(
    ifc_path,
    glb_path
):

    print()
    print("[7/7] Converting IFC → GLB...")
    print()

    # Import the existing working converter.
    #
    # Because rvt_to_glb.py is inside converter/,
    # Python can import ifc_to_glb.py directly.

    from ifc_to_glb import convert_ifc_to_glb

    convert_ifc_to_glb(
        str(ifc_path),
        str(glb_path)
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python converter\\rvt_to_glb.py "
            "input\\model.rvt"
        )

        sys.exit(1)

    input_file = Path(
        sys.argv[1]
    )

    # --------------------------------------------------------
    # Check input
    # --------------------------------------------------------

    if not input_file.exists():

        print(
            f"ERROR: File not found: {input_file}"
        )

        sys.exit(1)

    if input_file.suffix.lower() != ".rvt":

        print(
            "ERROR: Input file must be .rvt"
        )

        sys.exit(1)

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_ifc = (
        OUTPUT_DIR /
        f"{input_file.stem}_aps.ifc"
    )

    output_glb = (
        OUTPUT_DIR /
        f"{input_file.stem}.glb"
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    print("=" * 60)
    print("AUTODESK RVT → IFC → GLB CONVERTER")
    print("=" * 60)

    print(
        f"Input : {input_file}"
    )

    print(
        f"Output: {output_glb}"
    )

    # --------------------------------------------------------
    # APS authentication
    # --------------------------------------------------------

    token = get_access_token()

    # --------------------------------------------------------
    # Bucket
    # --------------------------------------------------------

    create_bucket(token)

    # --------------------------------------------------------
    # Upload RVT
    # --------------------------------------------------------

    object_data = upload_file(
        token,
        input_file
    )

    object_id = object_data[
        "objectId"
    ]

    # --------------------------------------------------------
    # RVT → IFC
    # --------------------------------------------------------

    urn = create_translation_job(
        token,
        object_id
    )

    manifest = wait_for_translation(
        token,
        urn
    )

    derivative_urn = find_ifc_derivative(
        manifest
    )

    download_derivative(
        token,
        urn,
        derivative_urn,
        output_ifc
    )

    # --------------------------------------------------------
    # IFC → GLB
    # --------------------------------------------------------

    convert_ifc_to_glb(
        output_ifc,
        output_glb
    )

    # --------------------------------------------------------
    # Finished
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("RVT → GLB CONVERSION COMPLETE")
    print("=" * 60)

    print()
    print(
        f"Final GLB: {output_glb}"
    )

    print()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()