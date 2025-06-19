import sqlite3

SQLITE_PATH = "data/mtgjson/AllPrintings.sqlite"

def dump_sqlite_schema(sqlite_path):
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables in {sqlite_path}:")
    for table in tables:
        print(f"\nTable: {table}")
        cursor.execute(f"PRAGMA table_info('{table}')")
        columns = cursor.fetchall()
        print("  Columns:")
        for col in columns:
            # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
            print(f"    {col[1]:<25} {col[2]:<15} {'NOT NULL' if col[3] else 'NULL'} "
                  f"DEFAULT {col[4]!r} {'PRIMARY KEY' if col[5] else ''}")
    conn.close()

if __name__ == "__main__":
    dump_sqlite_schema(SQLITE_PATH) 