from flask import Blueprint, request, Response
from urllib.parse import parse_qs
from playwright.sync_api import sync_playwright
import sys
import os
from common_code import common_module as cm
from datetime import datetime

proxy_blueprint = Blueprint('proxy_blueprint', __name__)

def parse_form_data(text):
    try:
        parsed = parse_qs(text)
        return {k: v[0] for k, v in parsed.items()}
    except Exception:
        return {}

def fetch_via_playwright_sync(url, data, headers, method='get'):
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)

        if headers:
            context.set_extra_http_headers(headers)

        if method.lower() == 'post':
            if headers.get("Content-Type", "").lower() == "application/json":
                response = context.request.post(url, data=data, headers=headers)
            else:
                response = context.request.post(url, form=data, headers=headers)

        if method.lower() == 'get':
            if headers.get("Content-Type", "").lower() == "application/json":
                response = context.request.get(url, data=data, headers=headers)
            else:
                response = context.request.get(url, form=data, headers=headers)

        html = response.text()
        browser.close()
        return html, 'text/html'

@proxy_blueprint.route('', methods=['GET', 'POST'])
def proxy_endpoint():
    if request.method == 'POST':
        if request.is_json:
            params = request.get_json()
        elif request.form:
            params = request.form.to_dict()
        else:
            params = request.args.to_dict()
    else:
        params = request.args.to_dict()

    url = params.get('url', '').strip()
    request_type = params.get('type', 'post').lower()
    if not url:
        return Response("URL is required", status=400, mimetype='text/plain')

    data = params.get('data', {})
    headers = params.get('headers', {})

    if isinstance(data, str):
        data = parse_form_data(data)

    if isinstance(headers, str):
        headers = parse_form_data(headers)

    try:
        log_dir = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'proxy_full_request_log.txt')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} - Params received: {params}\n")

    except Exception as e:
        print(f"Logging error: {e}")

    try:
        body, content_type = fetch_via_playwright_sync(url, data, headers, request_type)
        return Response(body, status=200, mimetype=content_type)
    except Exception as e:
        return Response(f"error: {str(e)}", status=500, mimetype='text/plain')
