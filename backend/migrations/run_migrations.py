import sqlite3
import os

def run_migrations():
    db_path = os.path.join(os.path.dirname(__file__), "..", "socratic.db")
    migrations_dir = os.path.join(os.path.dirname(__file__))
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create migrations table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS migrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        migration_name TEXT,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Get list of applied migrations
    cursor.execute("SELECT migration_name FROM migrations")
    applied = set(row[0] for row in cursor.fetchall())
    
    # Get all migration files
    migrations = []
    for file in os.listdir(migrations_dir):
        if file.endswith('.sql'):
            migrations.append(file)
    migrations.sort()
    
    # Apply new migrations
    for migration in migrations:
        if migration not in applied:
            print(f"Applying migration: {migration}")
            with open(os.path.join(migrations_dir, migration)) as f:
                sql = f.read()
                cursor.executescript(sql)
            cursor.execute("INSERT INTO migrations (migration_name) VALUES (?)", (migration,))
    
    conn.commit()
    conn.close()
    print("Migrations complete!")

if __name__ == "__main__":
    run_migrations()