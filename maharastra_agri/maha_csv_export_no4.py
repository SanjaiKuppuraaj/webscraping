import mysql.connector
import pandas as pd

# DB connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="sanjai",
    database="ecourts_db"
)

# Queries
q1 = """
SELECT 
    sno,
    case_no,
    'District Court' AS CourtType,
    cnr_no,
    AppearingFor,
    OpponentAs,
    new_act_type,
    district_name
FROM maha_disposed
WHERE AppearingFor = 'Petitioner'
  AND OpponentAs = 'Respondent'
GROUP BY cnr_no;
"""

q2 = """
SELECT 
    sno,
    case_no,
    'District Court' AS CourtType,
    cnr_no,
    AppearingFor,
    OpponentAs,
    new_act_type,
    district_name
FROM maha_disposed
WHERE AppearingFor = 'Respondent'
  AND OpponentAs = 'Petitioner'
GROUP BY cnr_no;
"""

# Read data
df1 = pd.read_sql(q1, conn)
df2 = pd.read_sql(q2, conn)

# Split case_no
def split_case_no(df):
    parts = df["case_no"].str.split("/", expand=True)
    df["case_type"] = parts[0]
    df["case_no"] = parts[1]
    df["case_year"] = parts[2]
    return df

df1 = split_case_no(df1)
df2 = split_case_no(df2)

# Rename columns
rename_map = {
    "sno": "Sl No",
    "cnr_no": "CNR",
    "new_act_type": "CF_field_dropdown_2634",
    "district_name": "CF_field_dropdown_2733",
    "case_type": "CaseType",
    "case_no": "CaseNumber",
    "case_year": "CaseYear"
}

df1 = df1.rename(columns=rename_map)
df2 = df2.rename(columns=rename_map)

# Merge both
final_df = pd.concat([df1, df2], ignore_index=True)

# Remove duplicates based on CNR
final_df = final_df.drop_duplicates(subset=["CNR"])

final_df.to_excel("Maharastra_act_feb_30.xlsx", index=False)
print("saved: Maharastra_act_jan_30.xlsx")

conn.close()










# import mysql.connector
# import pandas as pd
#
# conn = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password="sanjai",
#     database="ecourts_db"
# )
#
# q1 = """
# SELECT
#     sno,
#     case_no,
#     'District Court' AS CourtType,
#     cnr_no,
#     AppearingFor,
#     OpponentAs,
#     new_act_type,
#     district_name
# FROM maha_disposed
# WHERE AppearingFor='Petitioner'
#   AND OpponentAs='Respondent' group by cnr_no;
# """
#
# q2 = """
# SELECT
#     sno,
#     case_no,
#     'District Court' AS CourtType,
#     cnr_no,
#     AppearingFor,
#     OpponentAs,
#     new_act_type,
#     district_name
# FROM maha_disposed
# WHERE AppearingFor='Respondent'
#   AND OpponentAs='Petitioner' group by cnr_no;
# """
#
# df1 = pd.read_sql(q1, conn)
#
# df2 = pd.read_sql(q2, conn)
#
# def split_case_no(df):
#     parts = df["case_no"].str.split("/", expand=True)
#     df["case_type"] = parts[0]
#     df["case_no"] = parts[1]
#     df["case_year"] = parts[2]
#     return df
#
# df1 = split_case_no(df1)
# df2 = split_case_no(df2)
# # exit()
# rename_map = {
#     "sno": "Sl No",
#     "cnr_no": "CNR",
#     "new_act_type": "CF_field_dropdown_2634",
#     "district_name": "CF_field_dropdown_2733",
#     "case_type": "CaseType",
#     "case_no": "CaseNumber",
#     "case_year": "CaseYear"
# }
#
# df1 = df1.rename(columns=rename_map)
# df2 = df2.rename(columns=rename_map)
#
# final_df = pd.concat([df1, df2], ignore_index=True)
#
# final_df.drop_duplicates(subset=["CNR"])
#
# final_df.to_excel("Maharastra_act_jan_30.xlsx", index=False)
# print("saved: Maharastra_act_jan_30.xlsx")
#
# conn.close()
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
# # import mysql.connector
# # import pandas as pd
# #
# # conn = mysql.connector.connect(
# #     host="localhost",
# #     user="root",
# #     password="sanjai",
# #     database="ecourts_db"
# # )
# #
# # q1 = """
# # SELECT
# #     sno,
# #     'District Court' AS CourtType,
# #     cnr_no,
# #     AppearingFor,
# #     OpponentAs,
# #     new_act_type,
# #     district_name
# # FROM cases_disposed
# # WHERE AppearingFor='Petitioner'
# #   AND OpponentAs='Respondent';
# # """
# # df1 = pd.read_sql(q1, conn)
# # df1["QueryType"] = "Petitioner vs Respondent"
# # q2 = """
# # SELECT
# #     sno,
# #     'District Court' AS CourtType,
# #     cnr_no,
# #     AppearingFor,
# #     OpponentAs,
# #     new_act_type,
# #     district_name
# # FROM cases_disposed
# # WHERE AppearingFor='Respondent'
# #   AND OpponentAs='Petitioner';
# # """
# # df2 = pd.read_sql(q2, conn)
# # # df2["QueryType"] = "Respondent vs Petitioner"
# #
# # rename_map = {
# #     "sno": "Sl No",
# #     "cnr_no": "CNR",
# #     "new_act_type": "CF_field_dropdown_2634",
# #     "district_name": "CF_field_dropdown_2733"
# #
# # }
# #
# #
# # df1 = df1.rename(columns=rename_map)
# # df2 = df2.rename(columns=rename_map)
# # final_df = pd.concat([df1, df2], ignore_index=True)
# #
# # final_df.to_excel("Maharastra_act_[November].xlsx", index=False)
# # print("saved: Maharastra_act_[November].xlsx")
# #
# # conn.close()
# #
# #
# #
# #
# #
# #
# #
# #
# #
# #
# #
# #
# # # import mysql.connector
# # # import pandas as pd
# # #
# # # conn = mysql.connector.connect(
# # #     host="localhost",
# # #     user="root",
# # #     password="sanjai",
# # #     database="ecourts_db"
# # # )
# # #
# # # query = """
# # # SELECT
# # #     sno,
# # #     'District Court' AS CourtType,
# # #     cnr_no,
# # #     AppearingFor,
# # #     OpponentAs,
# # #     new_act_type,
# # #     district_name
# # # FROM cases_disposed
# # # WHERE AppearingFor='Petitioner'
# # #   AND OpponentAs='Respondent';
# # # """
# # #
# # # df = pd.read_sql(query, conn)
# # #
# # # df = df.rename(columns={
# # #     "sno": "Sl No",
# # #     "cnr_no": "CNR",
# # #     "new_act_type": "CF_field_dropdown_2634",
# # #     "district_name": "CF_field_dropdown_2733"
# # # })
# # #
# # # df.to_excel("Maharastra_act_[November].xlsx", index=False)
# # #
# # # print("saved: Maharastra_act_[November].xlsx")
# # #
# # #
# # #
# # #
# # #
# # #
# # #
# # #
# # #
# # #
# # #
# # #
# # #
# # #
# # # # import mysql.connector
# # # # import pandas as pd
# # # #
# # # # config = {
# # # #     'user': 'root',
# # # #     'password': 'sanjai',
# # # #     'host': 'localhost',
# # # #     'database': 'ecourts_db'
# # # # }
# # # # try:
# # # #     cnx = mysql.connector.connect(**config)
# # # #     cursor = cnx.cursor()
# # # #     disposed_query = "SELECT * FROM cases WHERE case_status = 'Disposed'"
# # # #     pending_query = "SELECT * FROM cases WHERE case_status = 'Pending'"
# # # #     with pd.ExcelWriter('cases.xlsx') as writer:
# # # #         pd.read_sql(disposed_query, cnx).to_excel(writer, sheet_name='Disposed', index=False)
# # # #         pd.read_sql(pending_query, cnx).to_excel(writer, sheet_name='Pending', index=False)
# # # #
# # # #     print("Data fetched and saved to cases.xlsx")
# # # #
# # # # except mysql.connector.Error as err:
# # # #     print("Error: {}".format(err))
# # # # finally:
# # # #     cursor.close()
# # # #     cnx.close()
