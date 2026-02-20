from flask import Flask, request, render_template, send_file, jsonify
import subprocess
import os
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>items</key>
    <array>
        <dict>
            <key>assets</key>
            <array>
                <dict>
                    <key>kind</key>
                    <string>software-package</string>
                    <key>url</key>
                    <string>{ipa_url}</string>
                </dict>
            </array>
            <key>metadata</key>
            <dict>
                <key>bundle-identifier</key>
                <string>{bundle_id}</string>
                <key>bundle-version</key>
                <string>1.0</string>
                <key>kind</key>
                <string>software</string>
                <key>title</key>
                <string>{app_name}</string>
            </dict>
        </dict>
    </array>
</dict>
</plist>
"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sign', methods=['POST'])
def sign_app():
    # Fájlok bekérése
    ipa = request.files.get('ipa')
    p12 = request.files.get('p12')
    prov = request.files.get('prov')
    pwd = request.form.get('password', '')
    app_name = request.form.get('app_name', 'SajatApp')
    bundle_id = request.form.get('bundle_id', 'com.sajat.app')

    if not all([ipa, p12, prov]):
        return jsonify({"error": "Hiányzó fájlok!"}), 400

    # Egyedi azonosító a munkamenethez
    session_id = str(uuid.uuid4())[:8]
    
    ipa_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_app.ipa")
    p12_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_cert.p12")
    prov_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_cert.mobileprovision")
    output_ipa = os.path.join(UPLOAD_FOLDER, f"{session_id}_signed.ipa")
    plist_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_manifest.plist")

    ipa.save(ipa_path)
    p12.save(p12_path)
    prov.save(prov_path)

    # Zsign parancs futtatása
    command = [
        "zsign", "-k", p12_path, "-p", pwd, "-m", prov_path,
        "-n", app_name, "-b", bundle_id, "-o", output_ipa, ipa_path
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        
        # --- JAVÍTÁS 1: HTTPS kikényszerítése ---
        base_url = request.host_url.rstrip('/')
        if base_url.startswith("http://"):
            base_url = base_url.replace("http://", "https://")
        
        ipa_url = f"{base_url}/download/{session_id}_signed.ipa"
        
        plist_content = PLIST_TEMPLATE.format(
            ipa_url=ipa_url, bundle_id=bundle_id, app_name=app_name
        )
        with open(plist_path, "w") as f:
            f.write(plist_content)
            
        plist_url = f"{base_url}/download/{session_id}_manifest.plist"
        install_url = f"itms-services://?action=download-manifest&url={plist_url}"

        return jsonify({
            "success": True,
            "install_url": install_url,
            "ipa_url": ipa_url
        })
        
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Hiba az aláírás során: {e.stderr}"}), 500

@app.route('/download/<filename>')
def download(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        # --- JAVÍTÁS 2: Pontos fájltípusok (MIME types) megadása az iOS-nek ---
        mimetype = 'application/octet-stream'
        if filename.endswith('.plist'):
            mimetype = 'text/xml'
        return send_file(file_path, mimetype=mimetype)
    return "Fájl nem található", 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
