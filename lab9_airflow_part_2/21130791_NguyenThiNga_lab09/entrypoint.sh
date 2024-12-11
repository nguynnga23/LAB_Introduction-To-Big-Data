#!/bin/bash

# Initialize the database
airflow db init

# Create an admin user if not already created
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

# Start the Airflow webserver
exec airflow webserver
