from flask import Blueprint, request, Response
import requests
import fitz  # PyMuPDF
from datetime import datetime
import json
import os
from PIL import Image
import pytesseract
from io import BytesIO
import gc
from common_code import common_module as cm

pdf_to_text_blueprint = Blueprint('pdf_to_text_blueprint', __name__)
os.environ["OMP_THREAD_LIMIT"] = "1"

def log_status(pdf_url, status):
    log_dir = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'pdf_to_text_log.txt')

    now = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    log_line = f"{now} | {pdf_url} | Status: {status}\n"
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_line)

@pdf_to_text_blueprint.route('', methods=['GET'])
def extract_pdf_text():
    pdf_url = request.args.get('url')

    if not pdf_url or not pdf_url.startswith("http"):
        log_status(pdf_url or 'MISSING_URL', "Invalid URL")
        return Response(
            json.dumps({"result": "error", "message": "No Record Found."}, ensure_ascii=False, indent=4),
            content_type='application/json; charset=utf-8',
            status=400
        )

    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        print(f"[INFO] Fetching URL: {pdf_url}")
        response = requests.get(pdf_url, headers=headers, timeout=40,stream=True)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()
        if not content_type.startswith("application/pdf"):
            log_status(pdf_url, f"Invalid Content-Type: {content_type}")
            return Response(
                json.dumps({"result": "error", "message": "No Record Found."}, ensure_ascii=False, indent=4),
                content_type='application/json; charset=utf-8',
                status=400
            )

        pdf = fitz.open(stream=response.content, filetype='pdf')
        text = '\n'.join(page.get_text("text", flags=0) for page in pdf)
        pdf.close()

        clean_text = text.replace('\uFFFD', '').strip()
        direct_text_length = len(clean_text)

        if not clean_text or "No Record Found" in clean_text:
            pdf_stream = BytesIO(response.content)
            doc = fitz.open(stream=pdf_stream, filetype="pdf")
            all_text = ""

            for page in doc:
                try:
                    # zoom = 1.5
                    zoom = 1.0
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)

                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    gray = img.convert("L")

                    custom_config = r'--psm 6'
                    # ocr_text = pytesseract.image_to_string(gray, lang='eng', config=custom_config)
                    ocr_text = pytesseract.image_to_string(gray, lang='hin+eng+tam+kan+mal', config=custom_config)

                    if not ocr_text.strip():
                        print(f"[WARN] OCR Empty on page {page.number}")
                        # gray.save(f"/tmp/ocr_page_{page.number}.png")  # Uncomment for debug

                    all_text += ocr_text.strip() + "\n\n"

                    del img, pix, gray
                    gc.collect()
                except Exception as e:
                    print(f"[ERROR] OCR Error on page {page.number}: {e}")

            doc.close()
            clean_text = all_text.strip()

        if not clean_text:
            log_status(pdf_url, f"No Record Found (OCR fallback), DirectTextLength={direct_text_length}")
            return Response(
                json.dumps({"result": "error", "message": "No Record Found."}, ensure_ascii=False, indent=4),
                content_type='application/json; charset=utf-8'
            )

        result = {"result": {"data": clean_text}}

        output_dir = os.path.join(cm.BASE_DIR_OUTPUTS, 'pdf_to_text')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'pdf_to_text.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        log_status(pdf_url, f"Completed, FinalTextLength={len(clean_text)}")
        gc.collect()

        return Response(
            json.dumps(result, ensure_ascii=False, indent=4),
            content_type='application/json; charset=utf-8'
        )

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else 'Unknown'
        headers = dict(e.response.headers) if e.response else {}
        log_status(pdf_url, f"HTTPError {status_code}: {str(e)}")
        return Response(
            json.dumps({"result": "error", "message": "No Record Found."}, ensure_ascii=False, indent=4),
            content_type='application/json; charset=utf-8',
            status=500
        )

    except requests.exceptions.RequestException as e:
        log_status(pdf_url, f"Fetch Failed: {type(e).__name__} - {str(e)}")
        return Response( json.dumps({"result": "error", "message": "No Record Found."}, ensure_ascii=False, indent=4),content_type='application/json; charset=utf-8',status=500)

    except (fitz.FileDataError, RuntimeError) as e:
        log_status(pdf_url, f"PDF Read Failed: {type(e).__name__} - {str(e)}")
        return Response(json.dumps({"result": "error", "message": "No Record Found."}, ensure_ascii=False, indent=4),content_type='application/json; charset=utf-8',status=500)
