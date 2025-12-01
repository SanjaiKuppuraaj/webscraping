import time
from pymongo import MongoClient
from hc_bombay import hc_bombay
import pprint

pp = pprint.PrettyPrinter(indent=2)

BENCH_MAP = {
    '01': 'Bombay',
    '02': 'Aurangabad',
    '03': 'Nagpur',
    '04': 'Goa'
}

M_SIDEFLG_MAP = {
    '01': {'C': 'Civil', 'CR': 'Criminal', 'OS': 'Original Side'},
    '02': {'AC': 'Civil', 'AR': 'Criminal'},
    '03': {'NC': 'Civil', 'NR': 'Criminal'},
    '04': {'GC': 'Civil', 'GR': 'Criminal'}
}

def get_side_flag_from_jurisdiction(bench_code_data, jurisdiction_name):
    side_map = M_SIDEFLG_MAP.get(bench_code_data, {})
    for flag, name in side_map.items():
        if name.lower() == jurisdiction_name.lower():
            return flag
    return jurisdiction_name

def normalize_party(party_data):
    if isinstance(party_data, str):
        return [party_data.strip()]
    elif isinstance(party_data, list):
        flat = []
        for item in party_data:
            if isinstance(item, str):
                flat.append(item.strip())
            elif isinstance(item, list):
                flat.extend(str(i).strip() for i in item)
            elif isinstance(item, dict):
                flat.append(str(item).strip())
            else:
                flat.append(str(item).strip())
        return flat
    elif isinstance(party_data, dict):
        return [str(party_data).strip()]
    else:
        return [str(party_data).strip()]

client = MongoClient("mongodb://localhost:27017/")
db = client["bombay_high_court"]
input_collection = db["state_of_maharashtra_OS"]

log_file = "/var/www/mml_python_code/hcb_db_status/data_log.txt"
docs = list(input_collection.find({'date_status': {'$ne': 'updated'}}))

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

for batch in chunks(docs, 5):
    for data in batch:
        doc_id = data['_id']
        bench_code = str(data.get('bench', '')).strip()
        side_code = str(data.get('jurisdiction', '')).strip()
        case_no = str(data.get('case_no', '')).strip()
        case_year = str(data.get('case_year', '')).strip()
        case_type = str(data.get('case_type', '')).strip()
        stamp = str(data.get('stamp', '')).strip()

        bench_code_data = next((code for code, name in BENCH_MAP.items() if name == bench_code), bench_code)
        side_flag = get_side_flag_from_jurisdiction(bench_code_data, side_code)
        stamp = 'R' if not stamp else 'S'

        process_str = f"Processing: {case_type}/{case_no}/{case_year}/{bench_code_data}/{side_flag}/{stamp}"

        try:
            scraper = hc_bombay(bench_code_data, side_flag, stamp, case_type, case_no, case_year)

            current_ip = scraper.get_current_ip()
            print(f"{process_str} | Using IP: {current_ip}")

            case_main_info = scraper.case_main_info()

            if (case_main_info.get("result") == "error"):
                status = "error"
            else:
                status = "updated"

            existing_petitioners = normalize_party(data.get('petitioner', []))
            new_petitioners = normalize_party(case_main_info.get('petitioner', []))
            merged_petitioners = sorted(list(set(existing_petitioners + new_petitioners)))

            existing_respondents = normalize_party(data.get('respondent', []))
            new_respondents = normalize_party(case_main_info.get('respondent', []))
            merged_respondents = sorted(list(set(existing_respondents + new_respondents)))
            update_data = {
                'petitioner': merged_petitioners,
                'respondent': merged_respondents,
                'date_status': status,
                **case_main_info
            }

            print(update_data)
            input_collection.update_one({'_id': doc_id}, {'$set': update_data})
            with open(log_file, "a") as f:
                f.write(f"{input_collection.name} | {process_str} | IP: {current_ip} | Status: {status}\n")

        except Exception as e:
            print(f"[ERROR] Failed processing document ID {doc_id}: {str(e)}")
            input_collection.update_one({'_id': doc_id}, {'$set': {'date_status': 'error'}})
            with open(log_file, "a") as f:
                f.write(f"{input_collection.name} | {process_str} | Status: Error - {str(e)}\n")

    print("Sleeping after batch...")
    # time.sleep(5)