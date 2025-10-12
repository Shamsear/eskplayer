from database import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute('SELECT COUNT(*) as total, MAX(played_at) as last_match FROM player_matches')
row = cur.fetchone()
print(f'Total matches: {row["total"]}, Last match: {row["last_match"]}')
conn.close()
