import argparse
import json
import os
from typing import Any, Dict, Iterable, List

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

DEFAULT_INPUT_DIR = os.path.join(os.path.dirname(__file__), "downloaded_trials")
DEFAULT_DATASET_NAME = "trialsfromhd"
DEFAULT_TABLE_NAME = "clinical_trials"
DEFAULT_LOCATION = "US"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload downloaded clinical trial JSON files to a BigQuery table."
    )
    parser.add_argument(
        "--project",
        help="Google Cloud project ID. If omitted, uses the default application credentials project.",
    )
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET_NAME,
        help="BigQuery dataset name where the trials table will be created or updated.",
    )
    parser.add_argument(
        "--table",
        default=DEFAULT_TABLE_NAME,
        help="BigQuery table name to write each trial row into.",
    )
    parser.add_argument(
        "--input-dir",
        default=DEFAULT_INPUT_DIR,
        help="Directory containing downloaded trial JSON files.",
    )
    parser.add_argument(
        "--location",
        default=DEFAULT_LOCATION,
        help="BigQuery dataset location to use when creating a new dataset.",
    )
    return parser.parse_args()


def find_trial_files(input_dir: str) -> List[str]:
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    return sorted(
        os.path.join(input_dir, filename)
        for filename in os.listdir(input_dir)
        if filename.endswith(".json") and filename != "manifest.json"
    )


def load_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def get_nct_id(trial_data: Dict, path: str) -> str:
    try:
        return trial_data["protocolSection"]["identificationModule"]["nctId"]
    except (KeyError, TypeError):
        return os.path.splitext(os.path.basename(path))[0]


def get_nested(data: Dict, *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def extract_trial_fields(trial_data: Dict, path: str) -> Dict[str, Any]:
    protocol = trial_data.get("protocolSection", {}) if isinstance(trial_data, dict) else {}

    return {
        "nct_id": get_nct_id(trial_data, path),
        "brief_title": get_nested(protocol, "identificationModule", "briefTitle"),
        "official_title": get_nested(protocol, "identificationModule", "officialTitle"),
        "overall_status": get_nested(protocol, "statusModule", "overallStatus"),
        "study_type": get_nested(protocol, "designModule", "studyType"),
        "phases": get_nested(protocol, "designModule", "phases", default=[]),
        "start_date": get_nested(protocol, "statusModule", "startDateStruct", "date"),
        "primary_completion_date": get_nested(
            protocol, "statusModule", "primaryCompletionDateStruct", "date"
        ),
        "completion_date": get_nested(protocol, "statusModule", "completionDateStruct", "date"),
        "lead_sponsor": get_nested(protocol, "sponsorCollaboratorsModule", "leadSponsor", "name"),
        "conditions": get_nested(protocol, "conditionsModule", "conditions", default=[]),
        "keywords": get_nested(protocol, "conditionsModule", "keywords", default=[]),
        "enrollment_count": get_nested(protocol, "designModule", "enrollmentInfo", "count"),
        "healthy_volunteers": get_nested(protocol, "eligibilityModule", "healthyVolunteers"),
        "sex": get_nested(protocol, "eligibilityModule", "sex"),
        "minimum_age": get_nested(protocol, "eligibilityModule", "minimumAge"),
        "brief_summary": get_nested(protocol, "descriptionModule", "briefSummary"),
        "has_results": trial_data.get("hasResults") if isinstance(trial_data, dict) else None,
        "trial": json.dumps(trial_data),
    }


def ensure_dataset(client: bigquery.Client, dataset_id: str, location: str) -> bigquery.DatasetReference:
    dataset_ref = client.dataset(dataset_id)
    try:
        client.get_dataset(dataset_ref)
    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = location
        client.create_dataset(dataset)
        print(f"Created BigQuery dataset: {dataset_id}")
    return dataset_ref


def ensure_table(client: bigquery.Client, dataset_ref: bigquery.DatasetReference, table_name: str) -> bigquery.TableReference:
    table_ref = dataset_ref.table(table_name)
    try:
        client.get_table(table_ref)
    except NotFound:
        schema = [
            bigquery.SchemaField("nct_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("brief_title", "STRING"),
            bigquery.SchemaField("official_title", "STRING"),
            bigquery.SchemaField("overall_status", "STRING"),
            bigquery.SchemaField("study_type", "STRING"),
            bigquery.SchemaField("phases", "STRING", mode="REPEATED"),
            bigquery.SchemaField("start_date", "STRING"),
            bigquery.SchemaField("primary_completion_date", "STRING"),
            bigquery.SchemaField("completion_date", "STRING"),
            bigquery.SchemaField("lead_sponsor", "STRING"),
            bigquery.SchemaField("conditions", "STRING", mode="REPEATED"),
            bigquery.SchemaField("keywords", "STRING", mode="REPEATED"),
            bigquery.SchemaField("enrollment_count", "INTEGER"),
            bigquery.SchemaField("healthy_volunteers", "BOOLEAN"),
            bigquery.SchemaField("sex", "STRING"),
            bigquery.SchemaField("minimum_age", "STRING"),
            bigquery.SchemaField("brief_summary", "STRING"),
            bigquery.SchemaField("has_results", "BOOLEAN"),
            bigquery.SchemaField("trial", "JSON", mode="REQUIRED"),
        ]
        table = bigquery.Table(table_ref, schema=schema)
        client.create_table(table)
        print(f"Created BigQuery table: {dataset_ref.dataset_id}.{table_name}")
    return table_ref


def build_rows(file_paths: Iterable[str]) -> List[Dict]:
    rows = []
    for path in file_paths:
        trial_data = load_json(path)
        rows.append(extract_trial_fields(trial_data, path))
    return rows


def upload_rows(client: bigquery.Client, table_ref: bigquery.TableReference, rows: List[Dict]) -> None:
    if not rows:
        print("No trial JSON files were found to upload.")
        return

    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        print("Failed to insert rows into BigQuery:")
        for error in errors:
            print(error)
        raise RuntimeError("BigQuery insert failed")

    print(f"Uploaded {len(rows)} trial rows to BigQuery table {table_ref.dataset_id}.{table_ref.table_id}.")


def main() -> None:
    args = parse_args()
    client = bigquery.Client(project=args.project) if args.project else bigquery.Client()

    file_paths = find_trial_files(args.input_dir)
    rows = build_rows(file_paths)

    dataset_ref = ensure_dataset(client, args.dataset, args.location)
    table_ref = ensure_table(client, dataset_ref, args.table)
    upload_rows(client, table_ref, rows)


if __name__ == "__main__":
    main()
