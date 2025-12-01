import pyarrow.parquet as pq

table = pq.read_table('your_data_file.parquet')
print(table.schema)
print(table.to_pandas().head())
