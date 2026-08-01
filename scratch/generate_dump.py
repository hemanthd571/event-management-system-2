import sys
import os
sys.path.append('d:/project3')
from app.dal import get_db_connection
from datetime import datetime, date, timedelta

conn = get_db_connection()
tables = ['users', 'events', 'event_registrations', 'venues', 'departments', 'approvals', 'event_comments', 'notifications']
dump = {}

def format_val(val):
    if val is None:
        return 'NULL'
    if isinstance(val, (datetime, date, timedelta)):
        return str(val)
    if isinstance(val, bool):
        return 'TRUE' if val else 'FALSE'
    if isinstance(val, str):
        # Escape newlines and pipes for markdown tables
        return val.replace('\n', ' ').replace('|', '\\|')
    return str(val)

try:
    with open(r'C:\Users\HEMANTH D\.gemini\antigravity-ide\brain\371b5d5b-2aa8-4a15-8484-784c20f36de7\database_dump.md', 'w', encoding='utf-8') as f:
        f.write('# Database Dump\n\n')
        with conn.cursor() as c:
            for t in tables:
                c.execute(f'SELECT * FROM {t}')
                rows = c.fetchall()
                f.write(f'## Table: `{t}`\n\n')
                if not rows:
                    f.write('*Table is empty*\n\n')
                    continue
                
                # Get column headers from the first row
                cols = list(rows[0].keys())
                f.write('| ' + ' | '.join(cols) + ' |\n')
                f.write('|' + '|'.join(['---' for _ in cols]) + '|\n')
                
                for row in rows:
                    row_vals = [format_val(row[col]) for col in cols]
                    f.write('| ' + ' | '.join(row_vals) + ' |\n')
                
                f.write('\n')
finally:
    conn.close()
print("Dump generated successfully!")
