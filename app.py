# -*- coding: utf-8 -*-
"""
海边照片墙 · 后端服务
运行方法：在这个文件夹打开命令行，执行  python app.py
然后浏览器打开 http://127.0.0.1:8000
"""
import os
import json
import time
import uuid
from flask import Flask, request, jsonify, send_from_directory, abort
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE, "uploads")
DATA_FILE = os.path.join(BASE, "data.json")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 单张最大 20MB

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"photos": [], "messages": []}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------- 页面 ----------
@app.route("/")
def index():
    return send_from_directory(BASE, "index.html")


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# ---------- 照片 API ----------
@app.route("/api/photos", methods=["GET"])
def get_photos():
    data = load_data()
    photos = [p for p in data["photos"] if os.path.exists(os.path.join(UPLOAD_DIR, p["file"]))]
    return jsonify(photos)


@app.route("/api/photos", methods=["POST"])
def upload_photo():
    f = request.files.get("photo")
    caption = (request.form.get("caption") or "").strip()[:50]
    nickname = (request.form.get("nickname") or "神秘朋友").strip()[:20]
    if not f or not f.filename:
        return jsonify({"error": "没有选择照片"}), 400

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": "只支持 jpg / png / gif / webp 图片"}), 400

    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)

    try:
        img = Image.open(f.stream)
        img.load()
        # 大图压缩，保证网页加载快
        if max(img.size) > 2000:
            img.thumbnail((2000, 2000))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        if ext in (".gif",):
            f.stream.seek(0)
            f.save(path)
        else:
            img.save(path, quality=88)
    except Exception:
        return jsonify({"error": "图片文件无法识别，请换一张试试"}), 400

    data = load_data()
    photo = {
        "file": filename,
        "caption": caption or "未命名照片",
        "nickname": nickname,
        "time": time.strftime("%Y-%m-%d %H:%M"),
    }
    data["photos"].insert(0, photo)
    save_data(data)
    return jsonify(photo), 201


@app.route("/api/photos/<file_id>", methods=["DELETE"])
def delete_photo(file_id):
    data = load_data()
    before = len(data["photos"])
    data["photos"] = [p for p in data["photos"] if p["file"] != file_id]
    if len(data["photos"]) == before:
        abort(404)
    try:
        os.remove(os.path.join(UPLOAD_DIR, file_id))
    except OSError:
        pass
    save_data(data)
    return jsonify({"ok": True})


# ---------- 留言 API ----------
@app.route("/api/messages", methods=["GET"])
def get_messages():
    return jsonify(load_data()["messages"])


@app.route("/api/messages", methods=["POST"])
def post_message():
    body = request.get_json(silent=True) or request.form
    name = (body.get("name") or "神秘朋友").strip()[:20]
    text = (body.get("text") or "").strip()[:200]
    if not text:
        return jsonify({"error": "留言内容不能为空"}), 400
    data = load_data()
    msg = {
        "name": name,
        "text": text,
        "time": time.strftime("%Y-%m-%d %H:%M"),
    }
    data["messages"].insert(0, msg)
    save_data(data)
    return jsonify(msg), 201


if __name__ == "__main__":
    print("=" * 46)
    print("  海边照片墙已启动！")
    print("  在浏览器打开:  http://127.0.0.1:8000")
    print("  按 Ctrl+C 可停止服务")
    print("=" * 46)
    app.run(host="0.0.0.0", port=8000, debug=False)
