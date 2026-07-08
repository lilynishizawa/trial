import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.parse import urlencode


API_URL = "https://clinicaltrials.gov/api/v2/studies"
DEFAULT_QUERY = "cancer"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "downloaded_trials")


def fetch_studies(query_term, page_size=10):
    params = {
        "format": "json",
        "query.term": query_term,
        "pageSize": page_size,
    }
    url = f"{API_URL}?{urlencode(params)}"

    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        data = json.load(response)

    studies = data.get("studies", [])
    if not studies:
        raise RuntimeError("No studies were returned by the API.")
    return studies


def save_studies(studies, output_dir=OUTPUT_DIR):
    os.makedirs(output_dir, exist_ok=True)

    manifest = []
    for index, study in enumerate(studies, start=1):
        study_info = study.get("protocolSection", {})
        identification = study_info.get("identificationModule", {})
        nct_id = identification.get("nctId", f"study_{index}")
        file_path = os.path.join(output_dir, f"{nct_id}.json")

        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(study, handle, indent=2)

        manifest.append({"index": index, "nct_id": nct_id, "file": file_path})

    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    return manifest


def main():
    query_term = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUERY
    studies = fetch_studies(query_term, page_size=10)
    manifest = save_studies(studies)

    print(f"Downloaded {len(manifest)} studies for query: {query_term}")
    for item in manifest:
        print(f"- {item['nct_id']} -> {item['file']}")


if __name__ == "__main__":
    main()
