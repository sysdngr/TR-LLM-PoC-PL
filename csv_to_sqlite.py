# This script loads a CSV file into an SQLite database.
# It prepares the database for use by the SQL agent, simulating production conditions.
# Converts the `all_players_with_details.csv` file into a table in `all_players_with_details.db`.


import pandas as pd
import sqlite3

csv_filename = 'all_players_with_details.csv'
db_filename = 'all_players_with_details.db'
table_name = 'all_players_with_details'

df = pd.read_csv(csv_filename)
conn = sqlite3.connect(db_filename)
df.to_sql(table_name, conn, if_exists='replace', index=False)
conn.close()
