import pandas as pd
import mysql.connector

conn = mysql.connector.connect(host="localhost",user="root",password="sanjai",database="ecourts_db")
cursor = conn.cursor(dictionary=True)

df = pd.read_excel("Agri_606_cases_missing_type.xlsx",sheet_name="Worksheet",engine="openpyxl")
cnr_list = df['CNR #'].tolist()
format_strings = ','.join(['%s'] * len(cnr_list))
query = f"""
    SELECT cnr_no, complex_name 
    FROM ecourts_db.maha_act 
    WHERE cnr_no IN ({format_strings})
"""

cursor.execute(query, tuple(cnr_list))
results = cursor.fetchall()

cnr_map = {row['cnr_no']: row['complex_name'] for row in results}
df['complex_name'] = df['CNR #'].map(cnr_map)
df.to_excel("Agri_606_cases_missing_type.xlsx", index=False,sheet_name="Worksheet")
cursor.close()
conn.close()









# import pandas as pd
# import mysql.connector
#
# conn = mysql.connector.connect(host="localhost",user="root",password="sanjai", database="ecourts_db")
#
# cursor = conn.cursor(dictionary=True)
#
# df = pd.read_excel("Agri_606_cases_missing_type.xlsx",
#     sheet_name="Worksheet",
#     engine="openpyxl")
#
# query = "SELECT * FROM maha_disposed WHERE cnr_no = %s"
# for cnr_no in df['CNR #']:
#     cursor.execute(query, (cnr_no,))
#     results = cursor.fetchall()
#     print(f"\nResults for {cnr_no}:")
#     for row in results:
#         complex_name = row['complex_name']
#         print(complex_name)
#
# cursor.close()
# conn.close()
