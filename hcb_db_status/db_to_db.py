import pandas as pd
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['bombay_high_court']
collection = db['state_of_maharashtra_OS']

chunk_size = 10000

for chunk in pd.read_csv('bombay_high_court.state_of_maharashtra_OS.csv', low_memory=False, chunksize=chunk_size):

    chunk = chunk.dropna(axis=1, how='all')
    chunk = chunk.loc[:, ~(chunk == '').all()]
    chunk = chunk.loc[:, ~chunk.columns.str.contains('^Unnamed')]
    chunk = chunk.fillna('')

    records = chunk.to_dict(orient='records')
    if records:
        collection.insert_many(records)
        print(f"Inserted {len(records)} documents into MongoDB chunk")
