
import mysql.connector
from mysql.connector import Error
import logging
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'sanjai'
DB_NAME = "ecourts_db"


def get_conn(create_db=False):
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        if create_db:
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} DEFAULT CHARACTER SET 'utf8mb4'")
            conn.commit()
            cursor.close()

        conn.database = DB_NAME
        return conn
    except Error as e:
        logging.error(f"MySQL connection error: {e}")
        raise

@contextmanager
def get_cursor(dictionary=True):
    conn = get_conn(create_db=True)
    cursor = conn.cursor(dictionary=dictionary, buffered=True)
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        logging.error(f"Database operation error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()







# # mysql_common.py
# import mysql.connector
# from mysql.connector import Error
# import logging
# from contextlib import contextmanager
#
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#
# def get_conn():
#     try:
#         conn = mysql.connector.connect(
#             host="localhost",
#             user="root",
#             password="sanjai",
#             # database="ecourts_db"
#             database="service_ecourt"
#         )
#         return conn
#     except Error as e:
#         logging.error(f"MySQL connection error: {e}")
#         raise
#
# @contextmanager
# def get_cursor(dictionary=True):
#     conn = get_conn()
#     cursor = conn.cursor(dictionary=dictionary, buffered=True)
#     try:
#         yield cursor
#         conn.commit()
#     except Exception as e:
#         conn.rollback()
#         logging.error(f"Database operation error: {e}")
#         raise
#     finally:
#         cursor.close()
#         conn.close()



# # mysql_common.py
# import mysql.connector
# from mysql.connector import Error
# import logging
# from contextlib import contextmanager
#
# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s'
# )
#
# def get_conn():
#     """
#     Establishes and returns a connection to the MySQL database.
#     Raises an exception if the connection fails.
#     """
#     try:
#         conn = mysql.connector.connect(
#             host="localhost",
#             user="root",
#             password="sanjai",
#             database="ecourts_db"
#         )
#         if conn.is_connected():
#             logging.info("Successfully connected to MySQL database")
#             return conn
#         else:
#             raise Error("Failed to connect to the MySQL database")
#     except Error as e:
#         logging.error(f"MySQL connection error: {e}")
#         raise
#
# @contextmanager
# def get_cursor(dictionary=True):
#     """
#     Context manager for MySQL cursor.
#     Commits changes on success and rolls back on exception.
#     Yields a cursor object.
#     """
#     conn = None
#     cursor = None
#     try:
#         conn = get_conn()
#         cursor = conn.cursor(dictionary=dictionary, buffered=True)
#         yield cursor
#         conn.commit()
#     except Exception as e:
#         if conn:
#             conn.rollback()
#         logging.error(f"Database operation error: {e}")
#         raise
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()
#
#
#
#
# # # mysql_common.py
# # import mysql.connector
# # from mysql.connector import Error
# # import logging
# # from contextlib import contextmanager
# #
# # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# #
# # def get_conn():
# #     try:
# #         conn = mysql.connector.connect(
# #             host="localhost",
# #             user="root",
# #             password="sanjai",
# #             database="ecourts_db"
# #         )
# #         return conn
# #     except Error as e:
# #         logging.error(f"Error connecting to MySQL: {e}")
# #         raise
# #
# # @contextmanager
# # def get_cursor(dictionary=True):
# #     conn = get_conn()
# #     cursor = conn.cursor(dictionary=dictionary)
# #     try:
# #         yield cursor
# #         conn.commit()
# #     except Exception as e:
# #         conn.rollback()
# #         logging.error(f"Error during DB operation: {e}")
# #         raise
# #     finally:
# #         cursor.close()
# #         conn.close()
#
#
