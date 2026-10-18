from flask import Flask, render_template, request, jsonify
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
import datetime
import os
import requests

app = Flask(__name__)

# Flask dan API Node.js di VPS yang sama -> pakai localhost.
# Kalau mau pakai URL tunnel, set env API_BASE.
API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:3001").rstrip("/")


def api_get(path, default=None):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return default


def api_post(path, payload, forwarded_ip=None):
    try:
        headers = {}
        if forwarded_ip:
            # Hantar IP pengunjung asal ke API Node
            headers['X-Forwarded-For'] = forwarded_ip

        r = requests.post(
            f"{API_BASE}{path}",
            json=payload,
            headers=headers,
            timeout=5
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def analisis_data(no_input):
    logs = []
    logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Memulakan imbasan OSINT...")
    try:
        if not no_input or not no_input.strip():
            logs.append("[!] Input kosong.")
            return {"logs": logs, "error": True}

        no_input = no_input.strip()
        if not no_input.startswith('+'):
            no_input = '+' + no_input

        logs.append(f"[*] Parsing nombor: {no_input}")
        parsed = phonenumbers.parse(no_input)

        is_valid = phonenumbers.is_valid_number(parsed)
        logs.append(f"[*] Status Validasi: {is_valid}")

        pembekal = carrier.name_for_number(parsed, "en")
        if pembekal and "YTL" in pembekal:
            pembekal = "Yes 5G (YTL)"
        logs.append(f"[*] Provider dikesan: {pembekal or 'Tidak Dikenali'}")

        zon = list(timezone.time_zones_for_number(parsed))
        logs.append(f"[*] Zon masa: {zon[0] if zon else 'Tidak Dikenali'}")

        data = {
            "status": "AKTIF / SAH" if is_valid else "TIDAK AKTIF / FORMAT SALAH",
            "negara": geocoder.description_for_number(parsed, "en") or "Tidak Dikenali",
            "kod_negara": parsed.country_code,
            "provider": pembekal if pembekal else "Tidak Dikenali",
            "zon_masa": zon[0] if zon else "Tidak Dikenali",
            "format": phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
            ),
            "link": f"https://www.truecaller.com/search?q={no_input[1:]}",
            "logs": logs
        }
        logs.append("[+] Analisis selesai dengan jayanya.")
        return data
    except phonenumbers.NumberParseException as e:
        logs.append(f"[!] Ralat parsing: {str(e)}")
        return {"logs": logs, "error": True}
    except Exception as e:
        logs.append(f"[!] Ralat: {str(e)}")
        return {"logs": logs, "error": True}


@app.route('/', methods=['GET', 'POST'])
def index():
    hasil = None
    if request.method == 'POST':
        no_tel = request.form.get('nombor', '')
        hasil = analisis_data(no_tel)

    views = api_get('/api/views', {'count': 0}) or {'count': 0}
    rate = api_get('/api/rate', {'total': 0, 'avg': 0}) or {'total': 0, 'avg': 0}
    comments = api_get('/api/comments', []) or []

    # Bump view tiap GET halaman + ambil IP sebenar pengunjung
    if request.method == 'GET':
        # --- BAHAGIAN YANG DIBETULKAN ---
        user_ip = request.headers.get('x-vercel-forwarded-for') or \
                  request.headers.get('x-real-ip') or \
                  request.headers.get('x-forwarded-for') or \
                  request.remote_addr
        
        # Hantar IP tersebut ke API Node
        bumped = api_post('/api/views', {}, forwarded_ip=user_ip)
        if bumped:
            views = bumped

    return render_template(
        'index.html',
        hasil=hasil,
        views=views.get('count', 0),
        rate=rate,
        comments=comments
    )


@app.route('/api/rate', methods=['POST'])
def proxy_rate():
    data = request.get_json(silent=True) or {}
    res = api_post('/api/rate', data)
    if res is None:
        return jsonify({'error': 'API down'}), 502
    return jsonify(res)


@app.route('/api/comments', methods=['POST'])
def proxy_comment():
    data = request.get_json(silent=True) or {}
    res = api_post('/api/comments', data)
    if res is None:
        return jsonify({'error': 'API down'}), 502
    return jsonify(res)


@app.route('/api/comments', methods=['GET'])
def proxy_comment_list():
    res = api_get('/api/comments', [])
    return jsonify(res)
