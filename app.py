from flask import Flask, render_template, request
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
import datetime

app = Flask(__name__)


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
    return render_template('index.html', hasil=hasil) 
