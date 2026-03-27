from flask import Flask, request, jsonify
from flask_cors import CORS
from twilio.rest import Client
import numpy as np
import librosa
import tensorflow as tf
import os
import uuid
import threading

app = Flask(__name__)

# ===============================
# CORS — allow all frontend origins
# ===============================
CORS(app, resources={r"/*": {"origins": "*"}})


# ===============================
# TWILIO CREDENTIALS
# (must be defined BEFORE routes use them)
# ===============================
account_sid      = "ACe9446cc382dda2d84e46c84081dce2ba"
auth_token       = "9d1c19188e11e3ec94a3cab58ad3e8a2"
twilio_number    = "+12138458765"
emergency_contact = "+917410938463"   # ← replace with real number

client = Client(account_sid, auth_token)


# ===============================
# LOAD TRAINED MODEL
# ===============================
MODEL_PATH = "/Users/harshkumarmishra16/Documents/Women Safety ai/backend/distress_model (1).h5"

model = tf.keras.models.load_model(MODEL_PATH)
print("✅ Model Loaded Successfully")
from datetime import datetime

def create_ai_summary(text, lat, lon, distress_level):
    location = f"{lat}, {lon}"

    return {
        "summary": f"User is in danger near {location}. Message: {text}. Immediate help required.",
        "location": location,
        "time": datetime.now().strftime("%H:%M"),
        "distress_level": distress_level,
        "keywords": text.lower().split()
    }


def send_emergency_alert(report):
    message = f"""
🚨 EMERGENCY ALERT
{report['summary']}

📍 Location: {report['location']}
⚠️ Level: {report['distress_level']}
⏰ Time: {report['time']}
    """

    client.messages.create(
        body=message,
        from_=twilio_number,
        to=emergency_contact
    )

    print("🚨 ALERT SENT")


# ===============================
# CAMERA STATE  (shared with YOLO thread)
# ===============================
camera_state = {
    "running":         False,
    "weapon_detected": False,
    "label":           ""
}


# ===============================
# FEATURE EXTRACTION
# ===============================
def extract_features(file_path):
    audio, sr = librosa.load(file_path, sr=22050)
    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=40)
    mfcc = np.mean(mfcc.T, axis=0)
    return mfcc


# ===============================
# YOLO WEAPON DETECTION  (runs in background thread)
# ===============================
def run_yolo_camera():
    """
    Runs YOLOv8 on the default webcam in a background thread.
    Detected weapon labels are written into camera_state so that
    the /camera-status endpoint can report them to the dashboard.
    """
    try:
        from ultralytics import YOLO
        import cv2

        yolo_model = YOLO("yolov8n.pt")   # downloads automatically on first run
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("❌ Could not open webcam for YOLO detection.")
            camera_state["running"] = False
            return

        print("📷 YOLO camera thread started.")

        while camera_state["running"]:
            ret, frame = cap.read()
            if not ret:
                break

            results = yolo_model(frame, verbose=False)

            weapon_found = False
            detected_label = ""

            for r in results:
                for box in r.boxes:
                    cls   = int(box.cls[0])
                    label = yolo_model.names[cls]
                    if label.lower() in ["knife", "gun", "pistol", "rifle", "weapon"]:
                        weapon_found  = True
                        detected_label = label
                        print(f"🚨 WEAPON DETECTED: {label}")
                        break
                if weapon_found:
                    break

            camera_state["weapon_detected"] = weapon_found
            camera_state["label"]           = detected_label

            # Optional: show local OpenCV window (comment out if running headless)
            cv2.imshow("Sakti AI — Camera", frame)
            if cv2.waitKey(1) == 27:   # ESC to quit window
                break

        cap.release()
        cv2.destroyAllWindows()
        print("📷 YOLO camera thread stopped.")

    except ImportError:
        print("⚠️  ultralytics / opencv not installed. "
              "Run: pip install ultralytics opencv-python")
        camera_state["running"] = False
    except Exception as e:
        print(f"❌ YOLO error: {e}")
        camera_state["running"] = False


# ═══════════════════════════════════════
#  ROUTES
# ═══════════════════════════════════════

# ── Home ──────────────────────────────
@app.route("/")
def home():
    return jsonify({"status": "Women Safety AI Backend Running 🚨"})


# ── Receive location from dashboard ───
@app.route("/location", methods=["POST"])
def location():
    data = request.json
    lat  = data.get("lat")
    lon  = data.get("lon")
    print(f"📍 USER LOCATION: {lat}, {lon}")
    return jsonify({"status": "Location received"})


# ── Send SMS via Twilio ───────────────
@app.route("/send-sms", methods=["POST"])
def send_sms():
    try:
        message = client.messages.create(
            body="🚨 EMERGENCY ALERT! Distress detected by Sakti AI. Please check immediately.",
            from_=twilio_number,
            to=emergency_contact
        )
        print(f"📱 SMS sent. SID: {message.sid}")
        return jsonify({"status": "SMS Sent", "sid": message.sid})

    except Exception as e:
        print(f"❌ SMS error: {e}")
        return jsonify({"status": "SMS Failed", "error": str(e)}), 500


# ── Send WhatsApp via Twilio Sandbox ──
@app.route("/send-whatsapp", methods=["POST"])
def send_whatsapp():
    try:
        message = client.messages.create(
            body="🚨 EMERGENCY! Distress detected by Sakti AI. Please check location immediately.",
            from_="whatsapp:+14155238886",        # Twilio sandbox number
            to=f"whatsapp:{emergency_contact}"    # must be registered in sandbox
        )
        print(f"💬 WhatsApp sent. SID: {message.sid}")
        return jsonify({"status": "WhatsApp Sent", "sid": message.sid})

    except Exception as e:
        print(f"❌ WhatsApp error: {e}")
        return jsonify({"status": "WhatsApp Failed", "error": str(e)}), 500


# ── Start YOLO camera in background ───
@app.route("/start-camera", methods=["POST"])
def start_camera():
    if camera_state["running"]:
        return jsonify({"status": "Camera already running"})

    camera_state["running"]         = True
    camera_state["weapon_detected"] = False
    camera_state["label"]           = ""

    thread = threading.Thread(target=run_yolo_camera, daemon=True)
    thread.start()

    print("📷 Camera thread launched.")
    return jsonify({"status": "Camera Started"})


# ── Stop YOLO camera ──────────────────
@app.route("/stop-camera", methods=["POST"])
def stop_camera():
    camera_state["running"] = False
    print("📷 Camera stop requested.")
    return jsonify({"status": "Camera Stopped"})


# ── Poll camera for weapon detections ─
@app.route("/camera-status", methods=["GET"])
def camera_status():
    """
    Dashboard polls this every 2 seconds.
    Returns current weapon detection state and resets the flag
    after reporting so each detection is only sent once.
    """
    detected = camera_state["weapon_detected"]
    label    = camera_state["label"]

    if detected:
        # Reset after reporting so it doesn't fire repeatedly
        camera_state["weapon_detected"] = False
        camera_state["label"]           = ""

    return jsonify({
        "running":         camera_state["running"],
        "weapon_detected": detected,
        "label":           label
    })


# ── AI Audio Prediction ───────────────
@app.route("/predict", methods=["POST"])
def predict():
    temp_path = None
    try:
        if "audio" not in request.files:
            return jsonify({"error": "Audio file not received"}), 400

        audio_file = request.files["audio"]

        filename  = f"temp_{uuid.uuid4().hex}.wav"
        temp_path = os.path.join(os.getcwd(), filename)
        audio_file.save(temp_path)
        print("🎤 Audio received")

        features = extract_features(temp_path)
        features = features.reshape(1, -1)

        prediction  = model.predict(features)
        probability = float(prediction[0][0])

        result = "Distress Detected" if probability > 0.5 else "Normal Voice"
        print(f"🔎 Prediction: {result}  (confidence: {probability:.3f})")

        # ✅ IMPORTANT: ANDAR hona chahiye
        lat = request.form.get("lat")
        lon = request.form.get("lon")
        text = request.form.get("text", "Voice distress detected")

        if result == "Distress Detected":

            report = create_ai_summary(text, lat, lon, "high")

            send_emergency_alert(report)

            return jsonify({
                "result": result,
                "confidence": probability,
                "report": report,
                "alert": "sent"
            })

        else:
            return jsonify({
                "result": result,
                "confidence": probability
            })

    except Exception as e:
        print(f"❌ Predict error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass


# ===============================
# RUN SERVER
# ===============================
if __name__ == "__main__":
    print("🚀 Starting Women Safety AI Server on http://127.0.0.1:8000")
    app.run(host="127.0.0.1", port=8000, debug=True)
if __name__ == "__main__":
    print("🚀 Starting Women Safety AI Server...")
    app.run(host="127.0.0.1", port=8000, debug=True)
  
