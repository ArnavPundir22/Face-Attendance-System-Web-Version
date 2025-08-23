import sqlite3
import pandas as pd

# --------------------------
# Config
# --------------------------
csv_file = "data.csv"
db_file = "database.db"   # SQLite DB
table_name = "students"
# --------------------------

# Load CSV
df = pd.read_csv(csv_file)

# Strip extra spaces from column names
df.columns = df.columns.str.strip()

# Map CSV columns to DB fields
df_to_insert = df.rename(columns={
    "CU - I'D": "ID",
    "NAME": "Name",
    "CONTACT NO.": "Mobile",
    "Email Address": "Gmail"
})

# Set Program and Branch for all
df_to_insert["Program"] = "B.Tech"
df_to_insert["Branch"] = "CSE"

# Optional: Strip spaces from string fields
for col in ["ID", "Name", "Program", "Branch", "Mobile", "Gmail"]:
    if col in df_to_insert.columns:
        df_to_insert[col] = df_to_insert[col].astype(str).str.strip()

# Connect to SQLite
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Create table if not exists
cursor.execute(f'''
CREATE TABLE IF NOT EXISTS {table_name} (
    ID TEXT PRIMARY KEY,
    Name TEXT,
    Program TEXT,
    Branch TEXT,
    Mobile TEXT,
    Gmail TEXT
)
''')

# Insert data
for _, row in df_to_insert.iterrows():
    try:
        cursor.execute(f'''
        INSERT OR REPLACE INTO {table_name} (ID, Name, Program, Branch, Mobile, Gmail)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (row["ID"], row["Name"], row["Program"], row["Branch"], row["Mobile"], row["Gmail"]))
        print(f"Inserted: {row['ID']} - {row['Name']}")
    except Exception as e:
        print(f"Error inserting {row['ID']}: {e}")

# Commit and close
conn.commit()
conn.close()
print("✅ All data inserted into database successfully.")
