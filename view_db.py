import sqlite3

def view_metrics():
    conn = sqlite3.connect('SoftwareMetricsCollector/instance/metrics.db')
    cursor = conn.cursor()
    
    # Get table schema
    cursor.execute("PRAGMA table_info(metric)")
    columns = cursor.fetchall()
    print("\nTable Schema:")
    for col in columns:
        print(f"Column: {col[1]}, Type: {col[2]}")
    
    # Get all data
    print("\nTable Contents:")
    cursor.execute("SELECT * FROM metric")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    
    conn.close()

if __name__ == "__main__":
    view_metrics() 