import sys
sys.path.insert(0, '/var/www/mml_python_code')
import sys
import os
import pandas as pd
from bs4 import BeautifulSoup
import re
from common_code import common_module as cm

output_folder = os.path.join(cm.BASE_DIR_OUTPUTS, 'new_supreme_causelist/output/')

matter_types = [
    '[DEFAULT / OTHER MATTERS]', '[SERVICE/COMPLIANCE]-BEFORE REGISTRAR(J)',
    '[TRANSFER PETITIONS]', '[BAIL MATTERS]', 'CHAMBER MATTERS',
    '[FRESH (FOR ADMISSION) - CIVIL CASES]', '[FRESH (FOR ADMISSION) - CRIMINAL CASES]',
    '[FRESHLY / ADJOURNED MATTERS]', 'PUBLIC INTEREST LITIGATIONS',
    '[AFTER NOTICE (FOR ADMISSION) - CIVIL CASES]', '[AFTER NOTICE (FOR ADMISSION) - CRIMINAL CASES]',
    '[DISPOSAL/FINAL DISPOSAL AT ADMISSION STAGE - CIVIL CASES]', '[ORDERS (INCOMPLETE MATTERS / IAs / CRLMPs)]',
    '[TOP OF THE LIST (FOR ADMISSION)]', 'AD INTERIM STAY MATTERS',
    "MISCELLANEOUS ADVANCE", "MISCELLANEOUS MAIN", "MISCELLANEOUS SUPPLEMENTARY",
    "REGULAR MAIN", "REGULAR SUPPLEMENTARY", "CHAMBER MAIN", "CHAMBER SUPPLEMENTARY",
    "SINGLE JUDGE MAIN", "SINGLE JUDGE SUPPLEMENTARY", "REVIEW & CURATIVE MAIN",
    "REVIEW & CURATIVE SUPPLEMENTARY", "REGISTRAR MAIN", "REGISTRAR SUPPLEMENTARY",
    "SUPPLEMENTARY LIST", "MISCELLANEOUS HEARING", "BAIL MATTERS",
    'Service Laws - Retiral benefits, pension', 'Criminal Law'
]
matter_types_upper = [m.upper().strip() for m in matter_types]

def is_special_header(text):
    headers = [
        'SUPREME COURT OF INDIA',
        'NOTE:-',
        'DAILY CAUSE LIST',
        'SUPPLEMENTARY LIST',
        'MISCELLANEOUS HEARING',
        'COURT NO. :'
    ]
    for h in headers:
        if h in text.upper():
            return h
    return False

def is_matter_type(text):
    return text.strip().upper() in matter_types_upper

def split_cells_on_br(text):
    return [part.strip() for part in text.replace('\n', '<br>').split('<br>') if part.strip()]

def pad_row_parts(parts_list, max_len):
    return parts_list + [''] * (max_len - len(parts_list))

def extract_main_case_number(text):
    generic_case_number_pattern = re.compile(
        r'([A-Z./\s()]{1,20}No\.?\s*\d{1,6}/\d{4})', re.IGNORECASE
    )
    matches = generic_case_number_pattern.findall(text)
    if matches:
        return matches[0].strip()
    return ""

def main():
    if len(sys.argv) < 3:
        print("❌ Usage: python supreme_html.py <input_csv_path> <output_json_path>")
        return

    csv_file = sys.argv[1]
    json_file = sys.argv[2]

    try:
        data = pd.read_csv(csv_file, on_bad_lines='skip')
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    data = data[data['Unnamed: 0'].astype(str).str.strip().str.upper() != 'SNO.']
    data.fillna("", inplace=True)

    html_string = data.to_html(index=False)
    soup = BeautifulSoup(html_string, 'html.parser')
    rows = soup.find_all('tr')

    merged_rows = []
    current_rows_stack = []
    current_special_block = None

    for tr in rows:
        tds = tr.find_all('td')
        if not tds:
            continue

        texts = [td.text.strip() for td in tds]
        non_empty_texts = [txt for txt in texts if txt]

        if not non_empty_texts:
            continue

        first_cell = texts[0]
        matched_header = is_special_header(first_cell)

        if matched_header:
            full_text = "<br>".join(non_empty_texts)
            current_special_block = [full_text]
            merged_rows.append((current_special_block, matched_header))
            current_rows_stack = []
            continue

        if is_matter_type(first_cell):
            merged_rows.append(([first_cell], 'MATTER_TYPE'))
            current_rows_stack = []
            continue

        if len(non_empty_texts) == 1:
            text_line = non_empty_texts[0]
            if current_rows_stack:
                ia_entries = re.split(r'(?=IA No\. \d+/\d{4})', text_line.strip(), flags=re.IGNORECASE)
                for row in current_rows_stack:
                    for ia_entry in ia_entries:
                        ia_entry = ia_entry.strip()
                        if not ia_entry:
                            continue
                        ia_entry = ia_entry.replace('\n', ' ').replace('<br>', ' ')
                        row[2] += f"<br><i>{ia_entry}</i>"
            else:
                merged_rows.append(([text_line], 'SINGLE_NOTE'))
            continue

        if first_cell:
            sno_parts = split_cells_on_br(tds[0].text)
            case_parts = split_cells_on_br(tds[1].text if len(tds) > 1 else "")
            raw_party_text = tds[2].text if len(tds) > 2 else ""
            party_lines = split_cells_on_br(raw_party_text)
            joined_party_text = " ".join(party_lines)

            case_no_text = tds[1].text if len(tds) > 1 else ""
            case_number_from_party = extract_main_case_number(joined_party_text)

            if case_no_text.strip().lower() in ["", "connected"] and case_number_from_party:
                case_parts = [case_number_from_party]
                joined_party_text = re.sub(re.escape(case_number_from_party), '', joined_party_text, flags=re.IGNORECASE).strip()

            versus_split = re.split(r'\bVersus\b', joined_party_text, flags=re.IGNORECASE)

            if len(versus_split) == 2:
                petitioner_text = versus_split[0].strip()
                rest_text = versus_split[1].strip()

                ia_notes = re.findall(r'(IA No\. .*?)(?=IA No\.|\Z)', rest_text, flags=re.IGNORECASE | re.DOTALL)
                rest_text_cleaned = re.sub(r'(IA No\. .*?)(?=IA No\.|\Z)', '', rest_text, flags=re.IGNORECASE | re.DOTALL).strip()

                respondent_block = rest_text_cleaned
                for note in ia_notes:
                    respondent_block += f"<br><i>{note.strip()}</i>"

                party_combined = f"{petitioner_text}<br><i>Versus</i><br>{respondent_block}"
                party_parts = [party_combined]
            else:
                party_parts = split_cells_on_br(raw_party_text)

            advocate_parts = split_cells_on_br(tds[3].text if len(tds) > 3 else "")

            max_len = max(len(sno_parts), len(case_parts), len(party_parts), len(advocate_parts))
            sno_parts = pad_row_parts(sno_parts, max_len)
            case_parts = pad_row_parts(case_parts, max_len)
            party_parts = pad_row_parts(party_parts, max_len)
            advocate_parts = pad_row_parts(advocate_parts, max_len)

            current_rows_stack = []
            for i in range(max_len):
                row = [sno_parts[i], case_parts[i], party_parts[i], advocate_parts[i]]
                merged_rows.append(row)
                current_rows_stack.append(row)
            continue

        if current_rows_stack:
            continuation_data = texts
            while len(continuation_data) < 4:
                continuation_data.append("")

            for row in current_rows_stack:
                for col in range(4):
                    content = continuation_data[col]
                    if content:
                        if row[col]:
                            row[col] += "<br>" + content
                        else:
                            row[col] = content

    final_html = """
    <html>
    <head>
        <title>Cause List</title>
        <style>
            body { font-family: Arial, sans-serif; }
            table { border-collapse: collapse; width: 100%; }
            td, th { border: 1px solid #aaa; padding: 6px; vertical-align: top; }
            .header-row { background-color: #f0f0f0; font-weight: bold; }
            .mattertype { background-color: #e0f0ff; color: #003366; font-weight: bold; text-align: center; }
            .court_num { background-color: #ffffcc; font-weight: bold; }
            .singleline { background-color: #fffbe6; font-style: italic; color: #444; text-align: left; }
            i { color: #666; font-size: 90%; }
        </style>
    </head>
    <body>
    <table>
    <tr><th>SNo.</th><th>Case No.</th><th>Petitioner / Respondent</th><th>Petitioner / Respondent Advocate</th></tr>
    """

    for row in merged_rows:
        if isinstance(row, tuple):
            block_text, tag = row
            if tag == 'MATTER_TYPE':
                final_html += f"<tr class='mattertype'><td colspan='4'><strong>{block_text[0]}</strong></td></tr>\n"
            elif tag == 'SINGLE_NOTE':
                final_html += f"<tr class='singleline'><td colspan='4'>{block_text[0]}</td></tr>\n"
            else:
                final_html += f"<tr class='header-row'><td colspan='4'><strong>{block_text[0]}</strong></td></tr>\n"
        else:
            sno, case_no, party_info, advocate = (row + [""] * 4)[:4]
            cells = [sno, case_no, party_info, advocate]
            formatted_cells = []
            for cell in cells:
                if "COURT NO. :" in cell.upper():
                    formatted_cells.append(f"<td class='court_num'><strong>{cell}</strong></td>")
                else:
                    formatted_cells.append(f"<td>{cell}</td>")
            final_html += "<tr>" + "".join(formatted_cells) + "</tr>\n"

    final_html += "</table>\n</body></html>"

    try:
        os.makedirs(output_folder, exist_ok=True)
        html_path = os.path.join(output_folder, "output.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(final_html)
        print(f"✅ HTML written to: {html_path}")
    except Exception as e:
        print(f"❌ Error writing HTML: {e}")

if __name__ == "__main__":
    main()