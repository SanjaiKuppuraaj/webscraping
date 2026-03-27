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
WHERE AppearingFor='Respondent'
  AND OpponentAs='Petitioner';
"""

print(q2)