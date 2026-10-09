import os
import sqlite3
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, send_from_directory, abort
)
from werkzeug.utils import secure_filename

# =========================================================
# KONFIGURASI
# =========================================================
app = Flask(__name__)
app.secret_key = "ganti-dengan-kunci-rahasia-anda"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
DATABASE = os.path.join(BASE_DIR, "lost_found.db")
ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "gif"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# DATABASE
# =========================================================
def get_db():
    conn = sqlite3.connect(DATABASE, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            jenis      TEXT NOT NULL,
            nama       TEXT NOT NULL,
            kategori   TEXT NOT NULL,
            ciri       TEXT,
            lokasi     TEXT NOT NULL,
            tanggal    TEXT NOT NULL,
            keterangan TEXT,
            foto       TEXT,
            status     TEXT DEFAULT 'belum',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_db()


# =========================================================
# HELPER
# =========================================================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def simpan_foto(file):
    if file and file.filename and allowed_file(file.filename):
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        fname = f"{stamp}_{secure_filename(file.filename)}"
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
        return fname
    return None


# =========================================================
# ROUTES
# =========================================================
@app.route("/")
def index():
    q        = request.args.get("q", "").strip()
    kategori = request.args.get("kategori", "").strip()
    jenis    = request.args.get("jenis", "").strip()
    status   = request.args.get("status", "").strip()

    sql = "SELECT * FROM items WHERE 1=1"
    params = []

    if q:
        sql += " AND (nama LIKE ? OR ciri LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if kategori:
        sql += " AND kategori = ?"
        params.append(kategori)
    if jenis:
        sql += " AND jenis = ?"
        params.append(jenis)
    if status:
        sql += " AND status = ?"
        params.append(status)

    sql += " ORDER BY created_at DESC"

    conn = get_db()
    items = conn.execute(sql, params).fetchall()
    conn.close()

    return render_template("index.html", items=items)


@app.route("/lapor/hilang", methods=["GET", "POST"])
def lapor_hilang():
    if request.method == "POST":
        foto = simpan_foto(request.files.get("foto"))
        conn = get_db()
        conn.execute("""
            INSERT INTO items
            (jenis, nama, kategori, ciri, lokasi, tanggal, keterangan, foto)
            VALUES ('hilang', ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.form["nama"],
            request.form["kategori"],
            request.form.get("ciri", ""),
            request.form["lokasi"],
            request.form["tanggal"],
            request.form.get("keterangan", ""),
            foto
        ))
        conn.commit()
        conn.close()
        flash("Laporan barang hilang berhasil dikirim.", "success")
        return redirect(url_for("index"))
    return render_template("lapor_hilang.html")


@app.route("/lapor/temuan", methods=["GET", "POST"])
def lapor_temuan():
    if request.method == "POST":
        foto = simpan_foto(request.files.get("foto"))
        conn = get_db()
        conn.execute("""
            INSERT INTO items
            (jenis, nama, kategori, ciri, lokasi, tanggal, keterangan, foto)
            VALUES ('temuan', ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.form["nama"],
            request.form["kategori"],
            request.form.get("ciri", ""),
            request.form["lokasi"],
            request.form["tanggal"],
            request.form.get("keterangan", ""),
            foto
        ))
        conn.commit()
        conn.close()
        flash("Laporan barang temuan berhasil dikirim.", "success")
        return redirect(url_for("index"))
    return render_template("lapor_temuan.html")


@app.route("/detail/<int:item_id>")
def detail(item_id):
    conn = get_db()
    item = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    conn.close()
    if not item:
        flash("Data tidak ditemukan.", "danger")
        return redirect(url_for("index"))
    return render_template("detail.html", item=item)


@app.route("/status/<int:item_id>", methods=["POST"])
def ubah_status(item_id):
    new_status = request.form.get("status", "belum")
    conn = get_db()
    conn.execute("UPDATE items SET status=? WHERE id=?", (new_status, item_id))
    conn.commit()
    conn.close()
    flash("Status berhasil diperbarui.", "success")
    return redirect(url_for("detail", item_id=item_id))


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# =========================================================
# JALANKAN
# =========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)