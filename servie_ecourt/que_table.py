import sys
sys.path.insert(0, '/var/www/mml_python_code')
import sys
import logging
from common_code.mysql_common import get_cursor
# from mysql_common import get_cursor

TRUNCATE = True
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_queue_table():
    with get_cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queue_table (
                id INT AUTO_INCREMENT PRIMARY KEY,
                state_code VARCHAR(10) NOT NULL,
                district_code VARCHAR(10) NOT NULL,
                est_code VARCHAR(20) NOT NULL,
                court_complex_id VARCHAR(20) NOT NULL,
                judge_id VARCHAR(255),
                status INT DEFAULT 0,
                attempts INT DEFAULT 0,
                error TEXT,
                causelist_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        try:
            cursor.execute("ALTER TABLE queue_table DROP INDEX unique_entry")
            logging.info("Dropped existing unique key to allow duplicates")
        except Exception as e:
            if "Can't DROP" not in str(e):
                raise

        cursor.execute(""" SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='queue_table' AND column_name='judge_id'""")
        if cursor.fetchone()['COUNT(*)'] == 0:
            cursor.execute("ALTER TABLE queue_table ADD COLUMN judge_id VARCHAR(255)")
            logging.info("Added judge_id column to queue_table")

        cursor.execute("""SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='queue_table' AND column_name='causelist_date'""")
        if cursor.fetchone()['COUNT(*)'] == 0:
            cursor.execute("ALTER TABLE queue_table ADD COLUMN causelist_date DATE")
            logging.info("Added causelist_date column to queue_table")

def populate_queue(state_code, dist_code=None, truncate=True):
    create_queue_table()
    with get_cursor() as cursor:
        if truncate:
            if dist_code:
                cursor.execute( "DELETE FROM queue_table WHERE state_code=%s AND district_code=%s", (state_code, dist_code) )
                logging.info(f"Cleared old rows for state_code={state_code}, district_code={dist_code}")
            else:
                cursor.execute( "DELETE FROM queue_table WHERE state_code=%s", (state_code,) )
                logging.info(f"Cleared old rows for state_code={state_code}")

        if dist_code:
            cursor.execute(""" SELECT est_id, complex_code, district_code, judge_id  FROM court_data WHERE state_code=%s AND district_code=%s """, (state_code, dist_code))
        else:
            cursor.execute(""" SELECT est_id, complex_code, district_code, judge_id FROM court_data  WHERE state_code=%s""", (state_code,))
        rows = cursor.fetchall()
        logging.info(f"Fetched {len(rows)} rows from court_data")

        inserted_count = 0
        skipped_count = 0
        missing_judge_id = 0

        for row in rows:
            if not row.get('judge_id'):
                missing_judge_id += 1

            if not truncate:
                cursor.execute(""" SELECT 1 FROM queue_table WHERE state_code=%s AND district_code=%s AND est_code=%s AND court_complex_id=%s AND judge_id=%s """, (state_code, row['district_code'], row['est_id'], row['complex_code'], row.get('judge_id')))
                if cursor.fetchone():
                    skipped_count += 1
                    continue

            cursor.execute(""" INSERT INTO queue_table (state_code, district_code, est_code, court_complex_id, judge_id, status, attempts, error) VALUES (%s,%s,%s,%s,%s,0,0,NULL)""", (state_code, row['district_code'], row['est_id'], row['complex_code'], row.get('judge_id')))
            inserted_count += 1

        logging.info(f"Inserted {inserted_count} new rows for state_code={state_code}" + (f", district_code={dist_code}" if dist_code else ""))
        if skipped_count > 0:
            logging.info(f"Skipped {skipped_count} existing rows")
        if missing_judge_id > 0:
            logging.warning(f"{missing_judge_id} rows have missing judge_id!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.error("Usage: python que_table.py <state_code> [district_code] [truncate]")
        sys.exit(1)

    state_code = sys.argv[1]
    dist_code = sys.argv[2] if len(sys.argv) > 2 else None
    if len(sys.argv) > 3:
        TRUNCATE = sys.argv[3].lower() in ("1", "true", "yes")

    populate_queue(state_code, dist_code, truncate=TRUNCATE)

# python3 que_table.py 3 20
