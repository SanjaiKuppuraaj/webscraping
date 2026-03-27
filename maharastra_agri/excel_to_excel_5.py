import pandas as pd

old_files = [
    "/home/jbk/webscraping_flask/maharastra_agri/sending_to_deepak/Maharastra_act_[November].xlsx",
    "/home/jbk/webscraping_flask/maharastra_agri/sending_to_deepak/Maharastra_acts_jan_8_2026.xlsx",
    "/home/jbk/webscraping_flask/maharastra_agri/sending_to_deepak/Maharastra_act_jan_30.xlsx",
    '/home/jbk/webscraping_flask/maharastra_agri/sending_to_deepak/Maharastra_acts_March_04.xlsx'
]

# new_file = "/home/jbk/webscraping_flask/maharastra_agri/sending_to_deepak/Maharastra_act_jan_30.xlsx"
new_file = '/home/jbk/webscraping_flask/maharastra_agri/Maharastra_act_mar_30.xlsx'
output_report = "/home/jbk/webscraping_flask/maharastra_agri/sending_to_deepak/new_report_CNR_not_matched_report.xlsx"

old_cnr_set = set()
for file in old_files:
    df = pd.read_excel(file)
    df["CNR"] = df["CNR"].astype(str).str.strip()
    old_cnr_set.update(df["CNR"])

new_df = pd.read_excel(new_file)
new_df["CNR"] = new_df["CNR"].astype(str).str.strip()
new_df = new_df.drop_duplicates(subset="CNR")
not_matched_df = new_df[~new_df["CNR"].isin(old_cnr_set)]
not_matched_df.to_excel(output_report, index=False)
print("Done.")
print(f"Non-matching CNR count: {len(not_matched_df)}")








# import pandas as pd
#
# # File paths
# file_1 = "/home/jbk/webscraping_flask/maharastra_agri/sending_to_deepak/Maharastra_act_[November].xlsx"
# file_2 = "/home/jbk/webscraping_flask/maharastra_agri/sending_to_deepak/Maharastra_acts_jan_8_2026.xlsx"
# file_3 = "/home/jbk/webscraping_flask/maharastra_agri/sending_to_deepak/Maharastra_act_jan_30.xlsx"
#
# # Output file
# output_report = "/home/jbk/webscraping_flask/maharastra_agri/sending_to_deepak/CNR_not_matched_report.xlsx"
#
# # Read excels
# df1 = pd.read_excel(file_1)
# df2 = pd.read_excel(file_2)
# df3 = pd.read_excel(file_3)
#
# # Normalize CNR (important to avoid fake mismatches)
# for df in [df1, df2, df3]:
#     df["CNR"] = df["CNR"].astype(str).str.strip()
#
# # Combine old CNRs
# existing_cnr = set(df1["CNR"]).union(set(df2["CNR"]))
#
# # Filter rows from Jan 30 that are NOT in previous files
# not_matched_df = df3[~df3["CNR"].isin(existing_cnr)]
#
# # Save report
# not_matched_df.to_excel(output_report, index=False)
#
# print(f"Report generated successfully: {output_report}")
# print(f"Total non-matching CNRs: {len(not_matched_df)}")
