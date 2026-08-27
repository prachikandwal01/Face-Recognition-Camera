import os
import io
import base64
from datetime import datetime
from typing import List

from flask import Flask, render_template, request, jsonify
import numpy as np
from PIL import Image
import face_recognition

APP_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWN_DIR = os.path.join(APP_DIR, "known_faces")

app = Flask(__name__)

# Globals holding encodings and names
known_encodings: List[np.ndarray] = []
known_names: List[str] = []


def load_known_faces():
    """Scan known_faces/<name>/*.jpg|png and build encodings."""
    global known_encodings, known_names
    known_encodings = []
    known_names = []

    if not os.path.isdir(KNOWN_DIR):
        os.makedirs(KNOWN_DIR, exist_ok=True)
        return

    for person in sorted(os.listdir(KNOWN_DIR)):
        person_dir = os.path.join(KNOWN_DIR, person)
        if not os.path.isdir(person_dir):
            continue
        for fname in os.listdir(person_dir):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            path = os.path.join(person_dir, fname)
            try:
                img = face_recognition.load_image_file(path)
                locs = face_recognition.face_locations(img)
                encs = face_recognition.face_encodings(img, locs)
                if not encs:
                    print(f"[WARN] No face found in {path}")
                    continue
                known_encodings.append(encs[0])
                known_names.append(person)
                print(f"[OK] Loaded {person} from {fname}")
            except Exception as e:
                print(f"[ERR] Failed {path}: {e}")


load_known_faces()


def dataurl_to_image(data_url: str) -> np.ndarray:
    """Convert a dataURL to an RGB numpy array."""
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    raw = base64.b64decode(data_url)
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    return np.array(img)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/identify", methods=["POST"])
def identify():
    payload = request.get_json(silent=True) or {}
    image_b64 = payload.get("image")
    if not image_b64:
        return jsonify({"ok": False, "error": "No image field."}), 400

    frame = dataurl_to_image(image_b64)

    # Detect faces & encode
    face_locations = face_recognition.face_locations(frame)
    face_encs = face_recognition.face_encodings(frame, face_locations)

    results = []
    for enc, (top, right, bottom, left) in zip(face_encs, face_locations):
        name = "Unknown"
        distance = None
        if known_encodings:
            distances = face_recognition.face_distance(known_encodings, enc)
            best_idx = int(np.argmin(distances))
            distance = float(distances[best_idx])
            matches = face_recognition.compare_faces(
                [known_encodings[best_idx]], enc, tolerance=0.5
            )
            if matches[0]:
                name = known_names[best_idx]
        results.append({
            "name": name,
            "box": {"top": int(top), "right": int(right),
                    "bottom": int(bottom), "left": int(left)},
            "distance": distance
        })

    return jsonify({"ok": True, "count": len(results), "results": results})


@app.route("/register", methods=["POST"])
def register():
    """Register a new person: expects JSON {name, image(dataURL)}"""
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    image_b64 = payload.get("image")

    if not name:
        return jsonify({"ok": False, "error": "Missing name"}), 400
    if not image_b64:
        return jsonify({"ok": False, "error": "Missing image"}), 400

    person_dir = os.path.join(KNOWN_DIR, name)
    os.makedirs(person_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(person_dir, f"{ts}.png")
    try:
        frame = dataurl_to_image(image_b64)
        Image.fromarray(frame).save(path)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to save image: {e}"}), 500

    # Rebuild encodings
    load_known_faces()

    return jsonify({"ok": True, "saved": path})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
