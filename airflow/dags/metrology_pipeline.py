from __future__ import annotations
import sys
import os
sys.path.insert(0, '/opt/airflow/src')
sys.path.insert(0, '/opt/airflow')

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime


def run_ingestion(**context):
    from ingestion.loaders import get_connection, init_bronze, load_measurements, load_environmental
    conn = get_connection()
    init_bronze(conn)
    n1 = load_measurements(conn)
    n2 = load_environmental(conn)
    conn.close()
    print(f"Loaded {n1} measurements and {n2} environmental records")


def run_monte_carlo(**context):
    sys.path.insert(0, '/opt/airflow/models')
    from monte_carlo import compute_and_store
    compute_and_store()


def run_predictive(**context):
    sys.path.insert(0, '/opt/airflow/models')
    from predictive import compute_and_store
    compute_and_store()


with DAG(
    dag_id="metrology_pipeline",
    start_date=datetime(2025, 1, 1),
    schedule_interval="0 6 * * 1-5",
    catchup=False,
) as dag:

    ingest_task = PythonOperator(
        task_id="ingest_bronze",
        python_callable=run_ingestion,
    )

    dbt_run_task = BashOperator(
        task_id="dbt_run",
        bash_command="docker exec metrology-platform-dbt-1 dbt run --profiles-dir /root/.dbt",
    )

    dbt_test_task = BashOperator(
        task_id="dbt_test",
        bash_command="docker exec metrology-platform-dbt-1 dbt test --profiles-dir /root/.dbt",
    )

    monte_carlo_task = PythonOperator(
        task_id="monte_carlo",
        python_callable=run_monte_carlo,
    )

    predictive_task = PythonOperator(
        task_id="predictive_maintenance",
        python_callable=run_predictive,
    )

    ingest_task >> dbt_run_task >> dbt_test_task >> [monte_carlo_task, predictive_task]