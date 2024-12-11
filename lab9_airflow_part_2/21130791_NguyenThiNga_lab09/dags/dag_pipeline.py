from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import re
from pymongo import MongoClient
from sqlalchemy import create_engine, text, Table, MetaData
from sqlalchemy.dialects.postgresql import insert
import psycopg2

def parse_email(email_text):
    try:
        return {
            "Message-ID": re.search(r"Message-ID:\s*<(.+?)>", email_text).group(1),
            "Date": re.search(r"Date:\s*(.+?)\n", email_text).group(1),
            "From": re.search(r"From:\s*(.+?)\n", email_text).group(1),
            "To": re.search(r"To:\s*(.+?)\n", email_text, re.DOTALL).group(1).replace("\n\t", ""),
            "Subject": re.search(r"Subject:\s*(.+?)\n", email_text).group(1),
            "Cc": re.search(r"Cc:\s*(.+?)\n", email_text, re.DOTALL).group(1).replace("\n\t", "") if re.search(r"Cc:\s*(.+?)\n", email_text) else None,
            "Bcc": re.search(r"Bcc:\s*(.+?)\n", email_text, re.DOTALL).group(1).replace("\n\t", "") if re.search(r"Bcc:\s*(.+?)\n", email_text) else None,
            "X-From": re.search(r"X-From:\s*(.+?)\n", email_text).group(1),
            "X-To": re.search(r"X-To:\s*(.+?)\n", email_text, re.DOTALL).group(1).replace("\n\t", ""),
            "X-cc": re.search(r"X-cc:\s*(.+?)\n", email_text, re.DOTALL).group(1).replace("\n\t", "") if re.search(r"X-cc:\s*(.+?)\n", email_text) else None,
            "X-bcc": re.search(r"X-bcc:\s*(.*)", email_text).group(1) if re.search(r"X-bcc:\s*(.*)", email_text) else None,
            "X-Folder": re.search(r"X-Folder:\s*(.+?)\n", email_text).group(1),
            "X-Origin": re.search(r"X-Origin:\s*(.+?)\n", email_text).group(1),
            "X-FileName": re.search(r"X-FileName:\s*(.+?)\n", email_text).group(1),
            "Body": email_text.split("\n\n", 1)[1].strip() if "\n\n" in email_text else None
        }
    except Exception as e:
        print(f"Error parsing email: {e}")
        return None
def normalize_column_names(columns):
    normalized_columns = []
    for col in columns:
        col = col.strip()
        col = col.lower()
        col = re.sub(r'[^\w\s]', '', col)
        col = re.sub(r'\s+', '_', col)
        normalized_columns.append(col)
    return normalized_columns
def extract_csv(file_dir, batch_size):
    
    data = pd.read_csv(file_dir).sample(batch_size)
    return data

file_dir = 'https://raw.githubusercontent.com/tnhanh/data-midterm-17A/refs/heads/main/email.csv'
batch_size = 200
mongo_info = {'client':'mongodb://root:example@mongodb:27017/',
               'db':'lab_data_mongo',
               'coll':'email_raw'
          }
ps_info = 'postgresql+psycopg2://airflow:airflow@postgres:5432/lab_data'

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 10, 28),
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

dag = DAG(
    'email_data_pipeline',
    default_args=default_args,
    description='A simple email data pipeline',
    schedule_interval='*/5 * * * *',  # Runs every 5 minutes
    catchup=False,
)

def mongo_job(**kwargs):
    
    data = extract_csv(file_dir, batch_size)
    data = data.to_dict(orient='records')
    print('Read and converted csv successfully')
    
    client = MongoClient(mongo_info['client'])
    db = client[mongo_info['db']] 
    collection = db[mongo_info['coll']]
    collection.insert_many(data)
    client.close()
    print('Load data into mongo successfully')

def postgres_job(**kwargs):
    
    client = MongoClient(mongo_info['client'])
    db = client[mongo_info['db']] 
    collection = db[mongo_info['coll']]
    print('Accessed mongo successfully')
    
    documents = collection.find()
    documents = list(documents)
    print('Extracted from mongo successfully')
    
    df_doc = pd.DataFrame(documents)
    df_doc.drop_duplicates('file',keep='first',inplace=True)
    df_doc = df_doc['message'].apply(parse_email).apply(pd.Series)
    df_doc.columns = normalize_column_names(df_doc.columns)
    df_doc['date'] = pd.to_datetime(df_doc['date'], errors='coerce')
    assert df_doc['messageid'].nunique()==df_doc.shape[0]
    print('Converted data into structured format successfully')

    engine = create_engine(ps_info)
    metadata = MetaData()
    table = Table('email_table', metadata, autoload_with=engine)

    insert_stmt = insert(table).values(df_doc.to_dict(orient='records'))
    do_nothing_stmt = insert_stmt.on_conflict_do_nothing(index_elements=['messageid']) 
    
    with engine.connect() as connection:
        transaction = connection.begin()  # Start a transaction
        try:
            connection.execute(do_nothing_stmt)  # Execute the upsert query
            transaction.commit()  # Commit the transaction if no error occurs
            print("Updated postgres target table successfully.")
        except Exception as e:
            transaction.rollback()  # Rollback the transaction if an error occurs
            print(f"Error: {e}")
            
    connection.close()
    client.close()

task_1 = PythonOperator(
        task_id='mongo_job',
        python_callable=mongo_job,
        dag=dag,

)

task_2 = PythonOperator(
        task_id='postgres_job',
        python_callable=postgres_job,
        dag=dag,

)

task_1 >> task_2