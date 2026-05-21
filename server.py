from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)
CORS(app)

# On Render free tier, /tmp is writable; locally uses project dir
if os.environ.get("FLASK_ENV") == "production":
    WAITLIST_FILE = "/tmp/waitlist.json"
else:
    WAITLIST_FILE = os.path.join(os.path.dirname(__file__), "waitlist.json")

NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "")
GMAIL_APP_PASS = os.environ.get("GMAIL_APP_PASS", "")


def send_notify(entry):
    if not NOTIFY_EMAIL or not GMAIL_APP_PASS:
        return
    try:
        body = (
            f"🎉 FlowMint AI 新候補 #{entry['id']}\n\n"
            f"名稱：{entry['name'] or '（未填）'}\n"
            f"Email：{entry['email']}\n"
            f"興趣：{entry['interest'] or '（未填）'}\n"
            f"時間：{entry['joined_at']}"
        )
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = f"[FlowMint] 新候補 #{entry['id']} — {entry['email']}"
        msg["From"] = NOTIFY_EMAIL
        msg["To"] = NOTIFY_EMAIL
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(NOTIFY_EMAIL, GMAIL_APP_PASS)
            s.send_message(msg)
    except Exception:
        pass  # 通知失敗不影響主流程


def load_waitlist():
    if not os.path.exists(WAITLIST_FILE):
        return []
    with open(WAITLIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waitlist(data):
    with open(WAITLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route("/")
def index():
    return send_from_directory(os.path.dirname(__file__), "index.html")


@app.route("/api/waitlist", methods=["POST"])
def join_waitlist():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip().lower()
    interest = (body.get("interest") or "").strip()

    if not email or "@" not in email:
        return jsonify({"error": "請填入有效的 Email"}), 400

    waitlist = load_waitlist()

    if any(e["email"] == email for e in waitlist):
        return jsonify({"error": "此 Email 已在候補名單中", "position": next(
            i + 1 for i, e in enumerate(waitlist) if e["email"] == email
        )}), 409

    entry = {
        "id": len(waitlist) + 1,
        "name": name,
        "email": email,
        "interest": interest,
        "joined_at": datetime.now().isoformat(),
    }
    waitlist.append(entry)
    save_waitlist(waitlist)
    send_notify(entry)

    return jsonify({
        "success": True,
        "position": entry["id"],
        "total": len(waitlist),
        "message": f"你是第 {entry['id']} 位加入候補！"
    })


@app.route("/api/waitlist/count", methods=["GET"])
def get_count():
    waitlist = load_waitlist()
    return jsonify({"count": len(waitlist)})


@app.route("/admin/waitlist", methods=["GET"])
def admin_list():
    waitlist = load_waitlist()
    return jsonify({"total": len(waitlist), "list": waitlist})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("FLASK_ENV") != "production"
    print(f"FlowMint 候補名單伺服器啟動中... port={port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
