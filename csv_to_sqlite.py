# This script loads a CSV into SQLite to simulate real deployment conditions,
# so a SQL agent can interact with an actual database as in production.


import pandas as pd
import sqlite3

csv_filename = 'premier_league_players_master.csv'
db_filename = 'premier_league_players_master.db'
table_name = 'premier_league_players_master'

df = pd.read_csv(csv_filename)
conn = sqlite3.connect(db_filename)
df.to_sql(table_name, conn, if_exists='replace', index=False)
conn.close()
