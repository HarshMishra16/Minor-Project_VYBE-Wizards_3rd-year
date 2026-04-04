"""
Sakti AI — Women Safety Backend  (with Emergency Chatbot + Evidence Recording)
===============================================================================
Run:   python app.py
Deps:  pip install flask flask-cors twilio tensorflow librosa numpy pydub soundfile
       brew install ffmpeg  (macOS)  OR  sudo apt install ffmpeg  (Linux)
       pip install ultralytics opencv-python   (optional — camera weapon detection)
       pip install google-auth                 (optional — Google OAuth verification)

Features:
  ✅ POST /predict        — AI voice distress detection
  ✅ POST /chatbot        — NLP emergency chatbot
  ✅ GET  /alerts         — chatbot alert log (SQLite)
  ✅ POST /recording/*    — auto video evidence recording
  ✅ POST /threat/signal  — drives recording state machine from YOLO
  ✅ GET  /recordings     — list saved evidence videos
"""

# ════════════════════════════════════════════════════════
# STANDARD LIBRARY — must come first, before any imports
# ════════════════════════════════════════════════════════
import os
import sys
import uuid
import threading
import hashlib
import random
import time
import traceback
import sqlite3

# ════════════════════════════════════════════════════════
# FLASK — import before evidence system (evidence_routes
# imports Flask internally; we must have it in sys.modules first)
# ════════════════════════════════════════════════════════
from flask import Flask, request, jsonify
from flask_cors import CORS

# ════════════════════════════════════════════════════════
# EVIDENCE SYSTEM — safe optional import
# BUG 1 FIX: wrapped in try/except with EVIDENCE_OK flag
# BUG 2 FIX: Flask imported above before this block
# ════════════════════════════════════════════════════════
_HERE          = os.path.dirname(os.path.abspath(__file__))
_EVIDENCE_PATH = os.path.join(_HERE, "evidence_system", "backend")

EVIDENCE_OK = False
if os.path.exists(_EVIDENCE_PATH) and _EVIDENCE_PATH not in sys.path:
    sys.path.insert(0, _EVIDENCE_PATH)

try:
    from evidence_routes  import register_evidence_routes
    from video_controller import get_controller as _get_video_controller
    EVIDENCE_OK = True
    print("✅ Evidence system imports successful")
except ImportError as _e:
    print(f"⚠️  Evidence system not loaded: {_e}")
    print("   Recording features disabled. "
          "Check evidence_system/backend/ folder exists.")

# ════════════════════════════════════════════════════════
# OPTIONAL DEPENDENCIES
# ════════════════════════════════════════════════════════
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_OK = True
except ImportError:
    TWILIO_OK = False
    print("⚠️  twilio not installed — pip install twilio")

try:
    import numpy as np
    NUMPY_OK = True
except ImportError:
    NUMPY_OK = False
    print("⚠️  numpy not installed — pip install numpy")

try:
    import librosa
    LIBROSA_OK = True
except ImportError:
    LIBROSA_OK = False
    print("⚠️  librosa not installed — pip install librosa")

try:
    import tensorflow as tf
    TF_OK = True
except ImportError:
    TF_OK = False
    print("⚠️  tensorflow not installed — pip install tensorflow")


# ════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════
TWILIO_ACCOUNT_SID = "AC60a8b082579f37e21246915687dcc8c5"
TWILIO_AUTH_TOKEN  = "8a0eace515ec06f84d09850a5f24db86"
TWILIO_NUMBER      = "+16414496345"
EMERGENCY_CONTACT  = "+917410938463"
GOOGLE_CLIENT_ID   = "460919756119-rq5q7b4fdde8dstk06n8nlfqtqg7qr7d.apps.googleusercontent.com"

# ── Model path (absolute, auto-search) ────────────────
MODEL_PATH = os.path.join(_HERE, "backend", "distress_model.h5")
if not os.path.exists(MODEL_PATH):
    for _candidate in [
        os.path.join(_HERE, "backend", "distress_model (1) 2.h5"),
        os.path.join(_HERE, "distress_model.h5"),
        os.path.join(_HERE, "distress_model (1) 2.h5"),
        os.path.join(_HERE, "distress_model (1).h5"),
        os.path.join(_HERE, "model.h5"),
    ]:
        if os.path.exists(_candidate):
            MODEL_PATH = _candidate
            break

DISTRESS_THRESHOLD = 0.5
DB_PATH            = os.path.join(_HERE, "sakti_alerts.db")


# ════════════════════════════════════════════════════════
# FLASK APP
# ════════════════════════════════════════════════════════
app = Flask(__name__)

# BUG 8 FIX: CORS must be registered BEFORE evidence routes
# so all routes (including evidence ones) get CORS headers
CORS(app,
     resources={r"/*": {"origins": "*"}},
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "OPTIONS"],
     supports_credentials=False)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        resp = app.make_default_options_response()
        resp.headers["Access-Control-Allow-Origin"]  = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return resp

# Evidence routes registered AFTER CORS (BUG 8 fix)
if EVIDENCE_OK:
    try:
        register_evidence_routes(app)
        print("✅ Evidence recording routes registered")
    except Exception as _e:
        print(f"⚠️  Evidence routes failed to register: {_e}")
        EVIDENCE_OK = False


# ════════════════════════════════════════════════════════
# TWILIO CLIENT
# ════════════════════════════════════════════════════════
twilio_client = None
if TWILIO_OK:
    try:
        twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        print("✅ Twilio client initialised")
    except Exception as e:
        print(f"⚠️  Twilio init failed: {e}")


# ════════════════════════════════════════════════════════
# LOAD AI DISTRESS MODEL
# ════════════════════════════════════════════════════════
model             = None
MODEL_INPUT_SHAPE = None

def load_model():
    global model, MODEL_INPUT_SHAPE
    if not TF_OK or not NUMPY_OK:
        print("⚠️  TensorFlow or NumPy unavailable — model not loaded")
        return

    print(f"\n📦 Loading model: {MODEL_PATH}")
    print(f"   File exists: {os.path.exists(MODEL_PATH)}")

    if not os.path.exists(MODEL_PATH):
        print("❌ Model file NOT FOUND.")
        print("   Fix: rename your .h5 to 'distress_model.h5' and place it next to app.py")
        return

    try:
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
        model       = tf.keras.models.load_model(MODEL_PATH, compile=False)
        input_shape = model.input_shape
        print(f"   Input shape : {input_shape}")
        print(f"   Output shape: {model.output_shape}")

        if len(input_shape) == 3:
            MODEL_INPUT_SHAPE = "3d"
            dummy = np.zeros((1, input_shape[1], input_shape[2]))
        else:
            MODEL_INPUT_SHAPE = "2d"
            dummy = np.zeros((1, input_shape[1] if input_shape[1] else 40))

        model.predict(dummy, verbose=0)
        print("✅ Model loaded and warmed up")

    except Exception as e:
        print(f"❌ Model load FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()
        model             = None
        MODEL_INPUT_SHAPE = None

load_model()


# ════════════════════════════════════════════════════════
# IN-MEMORY STORES
# ════════════════════════════════════════════════════════
users_db     = {}
otp_store    = {}
camera_state = {"running": False, "weapon_detected": False, "label": "", "streaming": False}

# Alert cooldown to prevent spam
last_alert_time = 0
ALERT_COOLDOWN = 5   # seconds

# Global frame buffer for streaming
latest_frame = None
frame_lock = threading.Lock()

# Stream security token
STREAM_TOKEN = "sakti123"

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


# ════════════════════════════════════════════════════════
# SQLITE — chatbot alert log
# ════════════════════════════════════════════════════════
def _init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chatbot_alerts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                message   TEXT NOT NULL,
                intent    TEXT NOT NULL,
                action    TEXT,
                lat       REAL,
                lon       REAL
            )
        """)
        conn.commit()
        conn.close()
        print(f"✅ SQLite DB ready: {DB_PATH}")
    except Exception as e:
        print(f"⚠️  DB init error: {e}")

def _log_alert(message, intent, action, lat=None, lon=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO chatbot_alerts (timestamp,message,intent,action,lat,lon) "
            "VALUES (?,?,?,?,?,?)",
            (time.strftime("%Y-%m-%d %H:%M:%S"), message, intent, action, lat, lon)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️  DB log error: {e}")

def _get_recent_alerts(limit=20):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.execute(
            "SELECT id,timestamp,message,intent,action,lat,lon "
            "FROM chatbot_alerts ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = [
            {"id":r[0],"timestamp":r[1],"message":r[2],
             "intent":r[3],"action":r[4],"lat":r[5],"lon":r[6]}
            for r in cur.fetchall()
        ]
        conn.close()
        return rows
    except Exception as e:
        print(f"⚠️  DB read error: {e}")
        return []

_init_db()


# ════════════════════════════════════════════════════════
# CHATBOT — NLP INTENT DETECTION
# ════════════════════════════════════════════════════════
INTENT_RULES = {
    "emergency": [
        "i am in danger", "send help", "someone following", "following me",
        "being followed", "please help", "save me", "rescue me", "in trouble",
        "call police", "call 911", "call 100", "call 112",
        "help", "danger", "emergency", "attacked", "attack",
        "unsafe", "scared", "afraid", "hurt", "abuse",
        "kidnap", "rape", "assault", "threat", "threatening",
        "stalker", "stalking", "harassing", "harassment"
    ],
    "weapon_alert": [
        "weapon", "knife", "gun", "pistol", "rifle", "armed",
        "shooting", "shot", "stabbed", "bomb", "explosive"
    ],
    "location": [
        "where am i", "share location", "send location",
        "location", "my location", "find me", "track me", "gps", "map"
    ],
    "status": [
        "am i safe", "is everything ok", "alert sent",
        "did you send", "was sms sent", "was alert sent", "status"
    ],
    "greeting": [
        "who are you", "what are you", "what can you do",
        "hello", "hi", "hey", "good morning", "good evening"
    ],
    "safe": [
        "i am safe", "i'm safe", "false alarm", "never mind",
        "stop alert", "i am ok", "i'm ok", "no danger", "cancel"
    ]
}

CHATBOT_RESPONSES = {
    "emergency":    "🚨 Emergency alert sent to your contacts. SMS and WhatsApp dispatched. Stay calm — help is on the way. Move to a safe, visible public place if possible.",
    "weapon_alert": "🚨 Weapon threat detected! Emergency alerts sent immediately. Move away from the threat. Call emergency services (100/112) if you can.",
    "location":     "📍 Sharing your live location with emergency contacts now. Stay where you are and keep your phone visible.",
    "status":       "✅ Your emergency contacts have been alerted. Check your SMS for confirmation. Reply 'help' at any time to send another alert.",
    "greeting":     "👋 I'm Sakti AI, your emergency safety assistant. Say 'help', 'I'm in danger', or 'share location' and I'll act instantly.",
    "safe":         "✅ Glad you're safe! Alert cancelled. I'm here if you need me again — just say 'help' anytime.",
    "normal":       "I'm your safety assistant. Say 'help', 'danger', 'call police', or 'share location' for instant emergency action. I'm always listening."
}

CHATBOT_ACTIONS = {
    "emergency":    "alert",
    "weapon_alert": "alert",
    "location":     "location",
    "status":       None,
    "greeting":     None,
    "safe":         None,
    "normal":       None
}

def detect_intent(message: str) -> str:
    msg = message.lower().strip()
    for intent, keywords in INTENT_RULES.items():
        for kw in sorted(keywords, key=len, reverse=True):
            if kw in msg:
                return intent
    return "normal"


# ════════════════════════════════════════════════════════
# CHATBOT ALERT DISPATCHER
# ════════════════════════════════════════════════════════
def _chatbot_dispatch_alerts(message: str, intent: str, lat=None, lon=None):
    if not twilio_client:
        print("⚠️  Twilio not configured — chatbot alerts skipped")
        return
    loc_str = (f"\n📍 Location: https://maps.google.com/?q={lat},{lon}"
               if lat and lon else "")
    body = (
        f"🚨 SAKTI AI CHATBOT ALERT\n"
        f"Message: \"{message}\"\n"
        f"Intent:  {intent.upper()}{loc_str}\n"
        f"Please respond immediately."
    )
    try:
        msg = twilio_client.messages.create(body=body, from_=TWILIO_NUMBER, to=EMERGENCY_CONTACT)
        print(f"📱 Chatbot SMS sent. SID: {msg.sid}")
    except Exception as e:
        print(f"❌ Chatbot SMS failed: {e}")
    try:
        msg = twilio_client.messages.create(
            body=body, from_="whatsapp:+14155238886",
            to=f"whatsapp:{EMERGENCY_CONTACT}")
        print(f"💬 Chatbot WhatsApp sent. SID: {msg.sid}")
    except Exception as e:
        print(f"❌ Chatbot WhatsApp failed: {e}")


# ════════════════════════════════════════════════════════
# AUDIO CONVERSION
# ════════════════════════════════════════════════════════
def convert_to_wav(src_path: str) -> str:
    wav_path = src_path.rsplit('.', 1)[0] + '_conv.wav'

    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(src_path)
        seg = seg.set_frame_rate(22050).set_channels(1).set_sample_width(2)
        seg.export(wav_path, format='wav')
        if os.path.exists(wav_path) and os.path.getsize(wav_path) > 100:
            print(f"🔄 pydub: {os.path.getsize(wav_path)} bytes")
            return wav_path
    except ImportError:
        print("   pydub not installed — trying ffmpeg")
    except Exception as e:
        print(f"   pydub failed: {e}")

    try:
        import subprocess
        r = subprocess.run(
            ['ffmpeg', '-y', '-i', src_path,
             '-ar', '22050', '-ac', '1', '-sample_fmt', 's16', wav_path],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0 and os.path.exists(wav_path):
            print(f"🔄 ffmpeg: {os.path.getsize(wav_path)} bytes")
            return wav_path
        print(f"   ffmpeg error: {r.stderr[-200:]}")
    except FileNotFoundError:
        print("   ffmpeg not found — brew install ffmpeg / sudo apt install ffmpeg")
    except Exception as e:
        print(f"   ffmpeg error: {e}")

    try:
        import soundfile as sf
        data, sr = sf.read(src_path)
        sf.write(wav_path, data, sr, subtype='PCM_16')
        print(f"🔄 soundfile: {os.path.getsize(wav_path)} bytes")
        return wav_path
    except Exception as e:
        print(f"   soundfile failed: {e}")

    print("⚠️  All conversion methods failed — passing raw file to librosa")
    return src_path


# ════════════════════════════════════════════════════════
# MFCC FEATURE EXTRACTION
# ════════════════════════════════════════════════════════
def extract_features(file_path: str):
    audio, sr = librosa.load(file_path, sr=22050, mono=True, duration=5.0)
    print(f"   Audio: {len(audio)} samples @ {sr}Hz  ({len(audio)/sr:.2f}s)")
    if len(audio) < 1000:
        raise ValueError(
            f"Audio too short ({len(audio)} samples). Speak for at least 2-3 seconds."
        )
    mfcc     = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=40)
    features = np.mean(mfcc.T, axis=0)
    print(f"   MFCC shape: {features.shape}  min={features.min():.2f}  max={features.max():.2f}")
    return features


# ════════════════════════════════════════════════════════
# VOICE ALERT DISPATCHER
# ════════════════════════════════════════════════════════
def send_emergency_alerts(reason="Distress Detected"):
    if not twilio_client:
        print("⚠️  Twilio not configured — voice alerts skipped")
        return
    stream_url = f"http://127.0.0.1:8000/video-feed?token={STREAM_TOKEN}"
    body = (f"🚨 SAKTI AI EMERGENCY ALERT\n"
            f"Reason: {reason}\n"
            f"📡 Live Stream: {stream_url}\n"
            f"Please check on her immediately.")
    try:
        msg = twilio_client.messages.create(body=body, from_=TWILIO_NUMBER, to=EMERGENCY_CONTACT)
        print(f"📱 Voice alert SMS sent. SID: {msg.sid}")
    except Exception as e:
        print(f"❌ Voice SMS failed: {e}")
    try:
        msg = twilio_client.messages.create(
            body=body, from_="whatsapp:+14155238886",
            to=f"whatsapp:{EMERGENCY_CONTACT}")
        print(f"💬 Voice alert WhatsApp sent. SID: {msg.sid}")
    except Exception as e:
        print(f"❌ Voice WhatsApp failed: {e}")


# ════════════════════════════════════════════════════════
# YOLO CAMERA STATE + EVIDENCE CONTROLLER BRIDGE
#
# BUG 3+4 FIX: _update_camera_and_controller is now a
#   proper module-level function, NOT nested inside the
#   while loop. Called correctly at the end of each frame.
#
# BUG 7+9 FIX: conf is passed as 0.0–1.0 float, not as
#   an integer percentage. Derived from box.conf[0] directly.
# ════════════════════════════════════════════════════════

COCO_WEAPON_CLASS_IDS = {49, 76}     # knife=49, scissors=76
CUSTOM_WEAPON_MODEL_PATH = "best_weapon.pt"
DETECTION_CONFIDENCE     = 0.25


def _update_camera_and_controller(
    weapon_found: bool,
    weapon_label: str,
    conf_float: float,      # 0.0–1.0  (BUG 9 fix: was conf_pct/100 previously)
    lat=None,
    lon=None,
):
    """
    Updates camera_state AND drives the VideoController state machine.
    Called once per processed YOLO frame.
    Module-level function — NOT nested inside run_yolo_camera().  (BUG 3 fix)
    """
    # 1. Update camera_state (read by /camera-status route)
    if weapon_found:
        camera_state["weapon_detected"] = True
        camera_state["label"]           = weapon_label
        camera_state["streaming"]       = True
        print(f"🚨 Threat detected: {weapon_label} - Streaming enabled")

        # Cooldown check to prevent spam alerts
        if time.time() - last_alert_time > ALERT_COOLDOWN:
            last_alert_time = time.time()
            threading.Thread(
                target=send_emergency_alerts,
                args=(f"Weapon detected: {weapon_label}",),
                daemon=True
            ).start()

    # 2. Drive evidence recording state machine
    if EVIDENCE_OK:
        try:
            ctrl = _get_video_controller()
            if weapon_found:
                ctrl.threat_detected(weapon_label, conf_float, lat, lon)
            else:
                ctrl.threat_cleared()
        except Exception as _e:
            print(f"⚠️  VideoController update failed: {_e}")


def _load_yolo_model():
    from ultralytics import YOLO
    if os.path.exists(CUSTOM_WEAPON_MODEL_PATH):
        print(f"🔫 Loading custom weapon model: {CUSTOM_WEAPON_MODEL_PATH}")
        return YOLO(CUSTOM_WEAPON_MODEL_PATH), True
    print("📦 Using yolov8n.pt (COCO-80) — knife=49, scissors=76")
    return YOLO("yolov8n.pt"), False


def _is_weapon(box, model_names: dict, is_custom: bool):
    cls_id = int(box.cls[0])
    conf   = float(box.conf[0])
    label  = model_names.get(cls_id, "unknown").lower().strip()
    if conf < DETECTION_CONFIDENCE:
        return False, "", 0.0
    if is_custom:
        return True, label, conf
    STRING_WEAPON_LABELS = {"knife","gun","pistol","rifle","weapon","scissors","sword","axe","blade"}
    if cls_id in COCO_WEAPON_CLASS_IDS or label in STRING_WEAPON_LABELS:
        return True, label, conf
    return False, "", 0.0


def run_yolo_camera():
    """
    Background thread: YOLO inference on each webcam frame.
    Writes to camera_state and drives the VideoController.
    """
    # BUG 5 FIX: cap.release() moved to finally block outside the while loop
    cap = None
    try:
        from ultralytics import YOLO
        import cv2

        global latest_frame

        yolo, is_custom = _load_yolo_model()

        print("📷 Camera opening (device 0)...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("   Device 0 failed — trying device 1...")
            cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("❌ Webcam unavailable on index 0 or 1.")
            camera_state["running"] = False
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        cap.set(cv2.CAP_PROP_FPS,          15)

        print(f"✅ YOLO camera thread running")
        print(f"   Model:      {'Custom: ' + CUSTOM_WEAPON_MODEL_PATH if is_custom else 'yolov8n.pt'}")
        print(f"   Confidence: ≥{DETECTION_CONFIDENCE}")

        frame_count = 0
        skip_frames = 4

        while camera_state["running"]:
            ret, frame = cap.read()
            if not ret:
                print("⚠️  Frame read failed — retrying...")
                time.sleep(0.1)
                continue

            # Update global frame buffer for streaming
            with frame_lock:
                latest_frame = frame.copy()
                print(f"📹 Frame updated: {frame.shape}")

            frame_count += 1
            if frame_count % skip_frames != 0:
                continue

            results = yolo.predict(
    frame,
    imgsz=320,        # 🔥 reduce size (default 640 → slower)
    conf=0.3,
    iou=0.4,
    device="cpu",     # or "cuda" if GPU available
    half=False        # True only if GPU
            )

            weapon_found = False
            weapon_label = ""
            weapon_conf  = 0.0   # BUG 7 FIX: always initialised before use

            for r in results:
                for box in r.boxes:
                    found, label, conf = _is_weapon(box, yolo.names, is_custom)
                    if found:
                        weapon_found = True
                        weapon_label = label
                        weapon_conf  = conf     # 0.0–1.0 float (BUG 9 fix)
                        print(f"🚨 WEAPON: {label.upper()}  "
                              f"conf={int(conf*100)}%  cls={int(box.cls[0])}")
                        break
                if weapon_found:
                    break

            # BUG 3+4 FIX: call the function (not define it!) here
            _update_camera_and_controller(
                weapon_found = weapon_found,
                weapon_label = weapon_label,
                conf_float   = weapon_conf,   # already 0.0–1.0
            )

            if frame_count % 30 == 0:
                all_labels = [
                    f"{yolo.names.get(int(box.cls[0]),'?')}({float(box.conf[0]):.2f})"
                    for r in results for box in r.boxes
                ]
                print(f"   Frame {frame_count}: " +
                      (', '.join(all_labels) if all_labels else "nothing detected"))

    except ImportError:
        print("❌ pip install ultralytics opencv-python")
        camera_state["running"] = False
    except Exception as e:
        print(f"❌ YOLO error: {type(e).__name__}: {e}")
        traceback.print_exc()
        camera_state["running"] = False
    finally:
        # BUG 5 FIX: cap always released here, even on exception
        if cap is not None:
            cap.release()
        print("📷 YOLO camera thread stopped cleanly.")


# ════════════════════════════════════════════════════════
# VIDEO STREAMING
# ════════════════════════════════════════════════════════
def generate_frames():
    global latest_frame
    print("🎥 generate_frames started")
    while True:
        with frame_lock:
            if latest_frame is None:
                print("⚠️ No frame available, waiting...")
                time.sleep(0.1)
                continue
            frame = latest_frame.copy()
        print(f"📸 Encoding frame: {frame.shape}")
        # Encode frame
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        print(f"📦 Frame size: {len(frame_bytes)} bytes")
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


# ════════════════════════════════════════════════════════
#   R O U T E S
# ════════════════════════════════════════════════════════

@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":          "Sakti AI Backend Running 🚨",
        "model_loaded":    model is not None,
        "twilio_ready":    twilio_client is not None,
        "librosa_ok":      LIBROSA_OK,
        "tensorflow_ok":   TF_OK,
        "numpy_ok":        NUMPY_OK,
        "chatbot":         "active",
        "evidence_system": "active" if EVIDENCE_OK else "disabled",
        "db_path":         DB_PATH,
    })


# ── Auth ──────────────────────────────────────────────

@app.route("/signup", methods=["POST"])
def signup():
    try:
        d    = request.get_json(force=True) or {}
        name = d.get("name","").strip()
        email= d.get("email","").strip().lower()
        phone= d.get("phone","").strip()
        pw   = d.get("password","")
        if not name or not email or not pw:
            return jsonify({"error": "Name, email and password required."}), 400
        if email in users_db:
            return jsonify({"error": "Account already exists."}), 409
        users_db[email] = {"name":name,"phone":phone,"password_hash":hash_pw(pw)}
        print(f"✅ Registered: {name} <{email}>")
        return jsonify({"status":"ok","message":"Account created."})
    except Exception as e:
        return jsonify({"error":str(e)}), 500


@app.route("/login", methods=["POST"])
def login():
    try:
        d    = request.get_json(force=True) or {}
        email= d.get("email","").strip().lower()
        pw   = d.get("password","")
        if not email or not pw:
            return jsonify({"error":"Email and password required."}), 400
        user = users_db.get(email)
        if not user or user["password_hash"] != hash_pw(pw):
            return jsonify({"error":"Invalid email or password."}), 401
        token = hash_pw(email + "sakti-secret")
        print(f"🔐 Login: {user['name']} <{email}>")
        return jsonify({"status":"ok","token":token,"name":user["name"]})
    except Exception as e:
        return jsonify({"error":str(e)}), 500


@app.route("/google-login", methods=["POST"])
def google_login():
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as g_req
        d    = request.get_json(force=True) or {}
        info = id_token.verify_oauth2_token(d.get("token",""), g_req.Request(), GOOGLE_CLIENT_ID)
        email, name = info["email"], info.get("name","User")
        if email not in users_db:
            users_db[email] = {"name":name,"phone":"","password_hash":""}
        return jsonify({"status":"ok","token":hash_pw(email+"google"),"name":name})
    except ImportError:
        return jsonify({"status":"ok","token":"dev-google","message":"Unverified (install google-auth)"})
    except Exception as e:
        return jsonify({"error":str(e)}), 401


@app.route("/send-otp", methods=["POST"])
def send_otp_route():
    try:
        phone = (request.get_json(force=True) or {}).get("phone","").strip()
        if not phone:
            return jsonify({"error":"Phone required"}), 400
        otp = str(random.randint(100000, 999999))
        otp_store[phone] = {"otp":otp,"expires":time.time()+300}
        print(f"📱 OTP for {phone}: {otp}")
        if twilio_client:
            try:
                twilio_client.messages.create(
                    body=f"Your Sakti AI OTP: {otp} (valid 5 min)",
                    from_=TWILIO_NUMBER, to=phone)
                return jsonify({"status":"sent"})
            except Exception as e:
                print(f"⚠️  OTP SMS failed: {e}")
        return jsonify({"status":"sent","otp":otp,"note":"dev mode — SMS not sent"})
    except Exception as e:
        return jsonify({"error":str(e)}), 500


@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    try:
        d     = request.get_json(force=True) or {}
        phone = d.get("phone","").strip()
        otp   = d.get("otp","").strip()
        rec   = otp_store.get(phone)
        if not rec:
            return jsonify({"error":"No OTP found."}), 400
        if time.time() > rec["expires"]:
            del otp_store[phone]
            return jsonify({"error":"OTP expired."}), 400
        if rec["otp"] != otp:
            return jsonify({"error":"Incorrect OTP."}), 401
        del otp_store[phone]
        if phone not in users_db:
            users_db[phone] = {"name":"User","phone":phone,"password_hash":""}
        return jsonify({"status":"ok","token":hash_pw(phone+"otp")})
    except Exception as e:
        return jsonify({"error":str(e)}), 500


@app.route("/location", methods=["POST"])
def location():
    d = request.get_json(force=True) or {}
    print(f"📍 Location received: {d.get('lat')}, {d.get('lon')}")
    return jsonify({"status":"received"})


@app.route("/send-sms", methods=["POST"])
def send_sms():
    if not twilio_client:
        return jsonify({"status":"SMS Failed","error":"Twilio not configured"}), 500
    try:
        msg = twilio_client.messages.create(
            body="🚨 EMERGENCY ALERT! Distress detected by Sakti AI.",
            from_=TWILIO_NUMBER, to=EMERGENCY_CONTACT)
        print(f"📱 SMS sent. SID: {msg.sid}")
        return jsonify({"status":"SMS Sent","sid":msg.sid})
    except Exception as e:
        print(f"❌ SMS error: {e}")
        return jsonify({"status":"SMS Failed","error":str(e)}), 500


@app.route("/send-whatsapp", methods=["POST"])
def send_whatsapp():
    if not twilio_client:
        return jsonify({"status":"WA Failed","error":"Twilio not configured"}), 500
    try:
        msg = twilio_client.messages.create(
            body="🚨 EMERGENCY! Distress detected by Sakti AI. Check her location.",
            from_="whatsapp:+14155238886",
            to=f"whatsapp:{EMERGENCY_CONTACT}")
        print(f"💬 WhatsApp sent. SID: {msg.sid}")
        return jsonify({"status":"WhatsApp Sent","sid":msg.sid})
    except Exception as e:
        print(f"❌ WhatsApp error: {e}")
        return jsonify({"status":"WA Failed","error":str(e)}), 500


@app.route("/start-camera", methods=["POST"])
def start_camera():
    if camera_state["running"]:
        return jsonify({"status":"Already running"})
    camera_state.update({"running":True,"weapon_detected":False,"label":"","streaming":False})
    threading.Thread(target=run_yolo_camera, daemon=True).start()
    print("📷 Camera thread launched.")
    return jsonify({"status":"Camera Started"})


@app.route("/stop-camera", methods=["POST"])
def stop_camera():
    camera_state["running"] = False
    return jsonify({"status":"Camera Stopped"})


@app.route("/camera-status", methods=["GET"])
def camera_status():
    detected = camera_state["weapon_detected"]
    label    = camera_state["label"]
    if detected:
        camera_state["weapon_detected"] = False
        camera_state["label"]           = ""
        print(f"📡 /camera-status: reported weapon '{label}' — state cleared")
    return jsonify({
        "running":         camera_state["running"],
        "weapon_detected": detected,
        "label":           label,
        "message":         f"⚠️ {label.upper()} detected!" if detected else "No threats detected"
    })


@app.route('/video-feed')
def video_feed():
    token = request.args.get("token")
    print(f"🔍 /video-feed called with token: {token}")
    if token != STREAM_TOKEN:
        print(f"❌ Token mismatch: got '{token}', expected '{STREAM_TOKEN}'")
        return "Unauthorized", 403
    if not camera_state.get("streaming", False):
        print("❌ Streaming not enabled - no active threat")
        return "No active threat", 403
    print("✅ Starting video stream...")
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# ════════════════════════════════════════════════════════
# /predict — AI VOICE DISTRESS DETECTION
# ════════════════════════════════════════════════════════
@app.route("/predict", methods=["POST", "OPTIONS"])
def predict():
    if request.method == "OPTIONS":
        resp = jsonify({"ok": True})
        resp.headers["Access-Control-Allow-Origin"]  = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return resp, 200

    temp_src = None
    temp_wav = None

    try:
        print("\n" + "="*52)
        print("🎤 /predict called")
        print(f"   Content-Type : {request.content_type}")
        print(f"   Files        : {list(request.files.keys())}")

        if "audio" not in request.files:
            print("❌ 'audio' key missing")
            return jsonify({"error":"No audio file received. FormData key must be 'audio'."}), 400

        audio_file = request.files["audio"]
        print(f"   Filename : {audio_file.filename}")
        print(f"   MIME     : {audio_file.mimetype}")

        temp_src  = os.path.join(os.getcwd(), f"tmp_{uuid.uuid4().hex}.webm")
        audio_file.save(temp_src)
        file_size = os.path.getsize(temp_src)
        print(f"   Saved    : {temp_src}  ({file_size} bytes)")

        if file_size < 500:
            return jsonify({
                "result":"Normal Voice","confidence":0.0,"distress":False,
                "note":"Audio too short. Speak clearly for 3–5 seconds."
            })

        print("🔄 Converting to WAV...")
        temp_wav  = convert_to_wav(temp_src)
        wav_exists = os.path.exists(temp_wav)
        wav_size   = os.path.getsize(temp_wav) if wav_exists else 0
        print(f"   WAV      : {temp_wav}  ({wav_size} bytes)")

        if not wav_exists or wav_size < 100:
            raise ValueError("WAV conversion failed. Fix: brew install ffmpeg AND pip install pydub")

        if not LIBROSA_OK:
            raise ImportError("librosa not installed — pip install librosa")
        if not NUMPY_OK:
            raise ImportError("numpy not installed — pip install numpy")

        print("📊 Extracting features...")
        raw_features = extract_features(temp_wav)

        if model is not None:
            in_shape = model.input_shape
            if len(in_shape) == 3:
                features = raw_features.reshape(1, in_shape[1], in_shape[2])
            else:
                features = raw_features.reshape(1, -1)
        else:
            features = raw_features.reshape(1, -1)

        print(f"   Feature shape: {features.shape}")

        if model is None:
            return jsonify({
                "result":"Model Not Loaded","confidence":0.0,"distress":False,"model_used":False,
                "error":"Model file not found or failed to load.",
                "fix":(f"Check MODEL_PATH in app.py. Currently: {MODEL_PATH}. "
                       f"File exists: {os.path.exists(MODEL_PATH)}. "
                       "Rename your .h5 file to remove spaces and restart Flask.")
            }), 503

        print("🤖 Running inference...")
        raw_output = model.predict(features, verbose=0)
        print(f"   Raw output : {raw_output}")

        if raw_output.shape[-1] == 1:
            prob        = float(raw_output[0][0])
            is_distress = prob > DISTRESS_THRESHOLD
        else:
            prob        = float(raw_output[0][1])
            is_distress = prob > DISTRESS_THRESHOLD

        result = "Distress Detected" if is_distress else "Normal Voice"
        print(f"   prob={prob:.6f}  result={result}")

        if is_distress:
            print("🚨 DISTRESS CONFIRMED — full emergency cascade")
            threading.Thread(
                target=send_emergency_alerts,
                args=(f"AI Voice Distress ({prob*100:.1f}% confidence)",),
                daemon=True
            ).start()
            if not camera_state["running"]:
                camera_state.update({"running":True,"weapon_detected":False,"label":"","streaming":False})
                threading.Thread(target=run_yolo_camera, daemon=True).start()
                print("📷 Camera auto-started by distress detection")
            _log_alert(
                message=f"Voice distress detected ({prob*100:.1f}%)",
                intent="voice_distress",
                action="sms+whatsapp+camera",
            )

        print(f"✅ /predict → {result} ({prob*100:.1f}%)")
        print("="*52 + "\n")

        return jsonify({
            "result":     result,
            "confidence": round(prob, 4),
            "distress":   is_distress,
            "model_used": True,
            "auto_triggered": {
                "sms":      is_distress,
                "whatsapp": is_distress,
                "camera":   is_distress,
            }
        })

    except Exception as e:
        print(f"❌ /predict ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
        return jsonify({"error":str(e),"type":type(e).__name__,"fix":_suggest_fix(e)}), 500

    finally:
        for p in set(filter(None, [temp_src, temp_wav])):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


def _suggest_fix(error: Exception) -> str:
    msg = str(error).lower()
    if "no backend" in msg or "audioread" in msg or "decode" in msg:
        return "Audio decode failed. brew install ffmpeg AND pip install pydub soundfile"
    if "ffmpeg" in msg:
        return "Install ffmpeg: macOS→ brew install ffmpeg | Ubuntu→ sudo apt install ffmpeg"
    if "empty" in msg or "short" in msg:
        return "Audio too short. Speak for at least 3 seconds."
    if "model" in msg or "h5" in msg or "keras" in msg:
        return f"Model file issue. Check MODEL_PATH: {MODEL_PATH}"
    if "librosa" in msg:
        return "pip install librosa"
    if "numpy" in msg:
        return "pip install numpy"
    if "reshape" in msg:
        return "Feature shape mismatch — check n_mfcc=40 matches your training config."
    return "Check Flask terminal for full traceback."


# ════════════════════════════════════════════════════════
# CHATBOT ROUTES
# ════════════════════════════════════════════════════════

@app.route("/chatbot", methods=["POST", "OPTIONS"])
def chatbot():
    if request.method == "OPTIONS":
        resp = jsonify({"ok": True})
        resp.headers.update({
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST, OPTIONS"
        })
        return resp, 200
    try:
        data    = request.get_json(force=True) or {}
        message = data.get("message","").strip()
        lat     = data.get("lat")
        lon     = data.get("lon")
        if not message:
            return jsonify({"error":"message is required"}), 400
        print(f"💬 Chatbot: '{message}'")
        intent = detect_intent(message)
        reply  = CHATBOT_RESPONSES.get(intent, CHATBOT_RESPONSES["normal"])
        action = CHATBOT_ACTIONS.get(intent)
        print(f"   Intent: {intent}  |  Action: {action}")
        if action == "alert":
            threading.Thread(
                target=_chatbot_dispatch_alerts,
                args=(message, intent, lat, lon),
                daemon=True
            ).start()
            _log_alert(message, intent, "sms+whatsapp", lat, lon)
        elif action == "location" and lat and lon:
            _log_alert(message, intent, "location_shared", lat, lon)
        else:
            _log_alert(message, intent, action or "none")
        return jsonify({"reply":reply,"intent":intent,"action":action})
    except Exception as e:
        print(f"❌ Chatbot error: {e}")
        traceback.print_exc()
        return jsonify({
            "reply":  "⚠️ I encountered an error. If this is an emergency, call 100 or 112.",
            "intent": "error", "action": None, "error": str(e)
        }), 500


@app.route("/alerts", methods=["GET"])
def get_alerts():
    try:
        limit  = int(request.args.get("limit", 20))
        alerts = _get_recent_alerts(limit)
        return jsonify({"alerts":alerts,"count":len(alerts)})
    except Exception as e:
        return jsonify({"error":str(e)}), 500


@app.route("/chatbot/intents", methods=["GET"])
def get_intents():
    return jsonify({
        "intents":  list(INTENT_RULES.keys()),
        "keywords": {k: v[:5] for k, v in INTENT_RULES.items()}
    })


# ════════════════════════════════════════════════════════
# STARTUP DIAGNOSTICS
# BUG 10 FIX: evidence_system status added to table
# ════════════════════════════════════════════════════════
def print_startup_diagnostics():
    ffmpeg_ok = os.system("ffmpeg -version > /dev/null 2>&1") == 0
    print("\n╔" + "═"*56 + "╗")
    print("║           SAKTI AI — STARTUP DIAGNOSTICS             ║")
    print("╠" + "═"*56 + "╣")
    checks = [
        ("Flask",            True),
        ("flask-cors",       True),
        ("numpy",            NUMPY_OK),
        ("librosa",          LIBROSA_OK),
        ("tensorflow",       TF_OK),
        ("twilio",           TWILIO_OK),
        ("ffmpeg",           ffmpeg_ok),
        ("Model file",       os.path.exists(MODEL_PATH)),
        ("Model loaded",     model is not None),
        ("SQLite DB",        os.path.exists(DB_PATH)),
        ("Chatbot",          True),
        ("Evidence system",  EVIDENCE_OK),   # BUG 10 fix
    ]
    for name, ok in checks:
        icon = "✅" if ok else "❌"
        print(f"║  {icon}  {name:<24} {'OK' if ok else 'MISSING / DISABLED':<24} ║")
    print("╠" + "═"*56 + "╣")
    print("║  Server:   http://127.0.0.1:8000                     ║")
    print("║  Health:   http://127.0.0.1:8000/health              ║")
    print("║  Chatbot:  POST /chatbot                             ║")
    print("║  Alerts:   GET  /alerts                              ║")
    if EVIDENCE_OK:
        print("║  Record:   POST /recording/start                    ║")
        print("║  Videos:   GET  /recordings                         ║")
    print("╚" + "═"*56 + "╝\n")

    if not os.path.exists(MODEL_PATH):
        print(f"⚠️  MODEL NOT FOUND: {MODEL_PATH}")
        print("   Rename your .h5 file to 'distress_model.h5' and place it next to app.py\n")
    if not LIBROSA_OK:
        print("❌ CRITICAL: pip install librosa\n")
    if not ffmpeg_ok:
        print("❌ CRITICAL: ffmpeg missing.")
        print("   macOS:  brew install ffmpeg")
        print("   Ubuntu: sudo apt install ffmpeg\n")
    if not EVIDENCE_OK:
        print("⚠️  Evidence system disabled.")
        print("   Check evidence_system/backend/ folder exists.\n")


# ════════════════════════════════════════════════════════
if __name__ == "__main__":
    print_startup_diagnostics()
    print("\n🔍 DEBUG: Registered routes:")
    print(app.url_map)
    print("="*60 + "\n")
    app.run(
        host="127.0.0.1",
        port=8000,
        debug=True,
        threaded=True,
        use_reloader=False
    )