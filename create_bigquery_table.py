import argparse

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

DEFAULT_PROJECT_ID = "lily123"
DEFAULT_DATASET_NAME = "trialsfromhd"
DEFAULT_TABLE_NAME = "clinical_trials"
DEFAULT_LOCATION = "US"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a BigQuery table for clinical trial data."
    )
    parser.add_argument("--project", default=DEFAULT_PROJECT_ID, help="Google Cloud project ID.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET_NAME, help="BigQuery dataset name.")
    parser.add_argument("--table", default=DEFAULT_TABLE_NAME, help="BigQuery table name to create.")
    parser.add_argument(
        "--location",
        default=DEFAULT_LOCATION,
        help="BigQuery dataset location to use when creating a new dataset.",
    )
    return parser.parse_args()


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


def create_table(client: bigquery.Client, dataset_ref: bigquery.DatasetReference, table_name: str) -> None:
    table_ref = dataset_ref.table(table_name)
    try:
        client.get_table(table_ref)
        print(f"Table already exists: {dataset_ref.dataset_id}.{table_name}")
        return
    except NotFound:
        pass

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


def main() -> None:
    args = parse_args()
    client = bigquery.Client(project=args.project)

    dataset_ref = ensure_dataset(client, args.dataset, args.location)
    create_table(client, dataset_ref, args.table)


if __name__ == "__main__":
    main()
