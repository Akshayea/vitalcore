# ============================================================
#  VitalCore — Flask Backend
#  Run:  python app.py
#  Then open: http://localhost:5000
# ============================================================
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3, json, os
from datetime import datetime, date, timedelta
print("🔥 App Starting...")

# ── App setup ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR)
CORS(app)

DB_PATH = os.path.join(BASE_DIR, "vitalcore.db")

# ── Database ─────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()

    c.execute("PRAGMA foreign_keys = ON;")

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            gender TEXT,
            weight REAL,
            height REAL,
            country TEXT,
            pa INTEGER,
            stress INTEGER,
            water REAL,
            sleep INTEGER,
            family TEXT,
            habits TEXT,
            bmi REAL,
            risk INTEGER,
            diseases TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Diary table
    c.execute("""
        CREATE TABLE IF NOT EXISTS diary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            mood TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Streaks
    c.execute("""
        CREATE TABLE IF NOT EXISTS streaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            day TEXT,
            UNIQUE(user_id, day)
        )
    """)

    # Tasks
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            day TEXT,
            tasks_json TEXT,
            UNIQUE(user_id, day)
        )
    """)

    conn.commit()
    conn.close()

    # Diary entries
    c.execute("""
        CREATE TABLE IF NOT EXISTS diary (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            text       TEXT NOT NULL,
            mood       TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Daily streaks
    c.execute("""
        CREATE TABLE IF NOT EXISTS streaks (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            day     TEXT NOT NULL,
            UNIQUE(user_id, day)
        )
    """)

    # Daily tasks state
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            day        TEXT NOT NULL,
            tasks_json TEXT NOT NULL,
            UNIQUE(user_id, day)
        )
    """)

    conn.commit()
    conn.close()

# ── Health calculation helpers ────────────────────────────────
def calc_disease(factors):
    return min(sum(factors), 95)

def calculate_health(data):
    name    = data.get("name", "User")
    age     = int(data.get("age", 25))
    gender  = data.get("gender", "Other")
    weight  = float(data.get("weight", 70))
    height  = float(data.get("height", 170))
    country = data.get("country", "India")
    pa      = int(data.get("pa", 3))
    stress  = int(data.get("stress", 3))
    water   = float(data.get("water", 2))
    sleep   = int(data.get("sleep", 7))
    family  = data.get("family", [])
    habits  = data.get("habits", [])

    bmi = weight / ((height / 100) ** 2)

    # Overall risk score
    risk = 0
    if bmi < 18.5 or bmi > 30: risk += 20
    elif bmi > 25:              risk += 10
    if stress >= 4: risk += 20
    elif stress == 3: risk += 10
    if pa <= 2: risk += 15
    elif pa == 3: risk += 5
    if water < 2:  risk += 10
    if sleep < 6 or sleep > 9: risk += 8
    if "smoking"   in habits: risk += 20
    if "alcohol"   in habits: risk += 12
    if "junk"      in habits: risk += 8
    if "sedentary" in habits: risk += 8
    if "heart"        in family: risk += 15
    if "diabetes"     in family: risk += 12
    if "cancer"       in family: risk += 10
    if "hypertension" in family: risk += 10
    if age > 50: risk += 10
    if age > 65: risk += 10
    risk = min(risk, 100)

    # Per-disease risks
    diseases = [
        {"name": "Type 2 Diabetes", "pct": calc_disease([
            25 if "diabetes" in family else 0,
            20 if bmi > 27 else 0,
            15 if pa <= 2 else 0,
            10 if "junk" in habits else 0,
            8  if stress >= 4 else 0
        ])},
        {"name": "Heart Disease", "pct": calc_disease([
            25 if "heart" in family else 0,
            20 if "smoking" in habits else 0,
            10 if "alcohol" in habits else 0,
            12 if stress >= 4 else 0,
            10 if bmi > 30 else 0,
            10 if age > 45 else 0
        ])},
        {"name": "Hypertension", "pct": calc_disease([
            20 if "hypertension" in family else 0,
            20 if stress >= 4 else 0,
            15 if "smoking" in habits else 0,
            10 if water < 2 else 0,
            10 if pa <= 2 else 0
        ])},
        {"name": "Obesity Risk", "pct": calc_disease([
            30 if bmi > 25 else 0,
            20 if "junk" in habits else 0,
            20 if pa <= 2 else 0,
            15 if "sedentary" in habits else 0,
            5  if stress >= 4 else 0
        ])},
        {"name": "Mental Stress", "pct": calc_disease([
            35 if stress >= 4 else 0,
            20 if sleep < 6 else 0,
            10 if "screen" in habits else 0,
            15 if "latenight" in habits else 0,
            5  if water < 2 else 0
        ])},
        {"name": "Cancer Risk", "pct": calc_disease([
            25 if "cancer" in family else 0,
            20 if "smoking" in habits else 0,
            10 if "alcohol" in habits else 0,
            15 if age > 50 else 0
        ])},
    ]

    return {
        "name": name, "age": age, "gender": gender,
        "weight": weight, "height": height, "country": country,
        "pa": pa, "stress": stress, "water": water, "sleep": sleep,
        "family": family, "habits": habits,
        "bmi": round(bmi, 2), "risk": risk, "diseases": diseases
    }

def build_diet_plan(data):
    family = data.get("family", [])
    habits = data.get("habits", [])
    water  = float(data.get("water", 2))

    diet = [
        {"ico": "🥦", "txt": "Leafy greens & cruciferous vegetables", "sub": "Broccoli, spinach, kale — 2 servings daily"},
        {"ico": "🐟", "txt": "Lean protein sources", "sub": "Fish, chicken, legumes, tofu — every meal"},
        {"ico": "🫐", "txt": "Antioxidant-rich fruits", "sub": "Berries, pomegranate, citrus — 2 servings"},
        {"ico": "🌾", "txt": "Whole grains only", "sub": "Brown rice, oats, quinoa — over refined carbs"},
        {"ico": "💧", "txt": f"Drink {max(water+1, 2.5):.1f}L+ water daily", "sub": "Start with a glass of warm water each morning"},
        {"ico": "🥜", "txt": "Healthy fats", "sub": "Almonds, walnuts, olive oil, avocado"},
    ]
    if "diabetes" in family:
        diet.append({"ico": "🚫", "txt": "Low glycemic index foods", "sub": "Control blood sugar — avoid sugary drinks"})
    if "heart" in family:
        diet.append({"ico": "🧄", "txt": "Heart-healthy foods", "sub": "Garlic, omega-3s, fiber — daily routine"})

    avoid = [
        {"ico": "🍔", "txt": "Ultra-processed foods", "sub": "Chips, fast food, packaged snacks"},
        {"ico": "🧂", "txt": "Excess sodium", "sub": "Keep under 2300mg/day — watch labels"},
        {"ico": "🥤", "txt": "Sugary beverages", "sub": "Soda, juices, energy drinks"},
        {"ico": "🍞", "txt": "Refined carbohydrates", "sub": "White bread, pastries, white rice"},
    ]
    if "smoking" in habits:
        avoid.append({"ico": "🚬", "txt": "Tobacco in all forms", "sub": "Primary cause of preventable death"})
    if "alcohol" in habits:
        avoid.append({"ico": "🍺", "txt": "Alcohol", "sub": "Limit to zero or very occasional"})

    do_list = [
        {"ico": "😴", "txt": "Sleep 7-8 hours", "sub": "Non-negotiable for cellular repair & hormones"},
        {"ico": "🚶", "txt": "30 min walk daily", "sub": "Best low-cost health investment"},
    ]

    return {"diet": diet, "avoid": avoid, "do": do_list}

# ── Default tasks ─────────────────────────────────────────────
DEFAULT_TASKS = [
    {"label": "💧 Drink 8 glasses of water",    "done": False},
    {"label": "🚶 30 min walk or exercise",      "done": False},
    {"label": "🥗 Eat a healthy meal",           "done": False},
    {"label": "😴 Sleep by 11 PM",              "done": False},
    {"label": "🧘 5 min meditation / breathing", "done": False},
    {"label": "📔 Write a diary entry",         "done": False},
    {"label": "📵 No screens 1hr before bed",   "done": False},
]

# ════════════════════════════════════════════════════════════
#  ROUTES — Serve HTML
# ════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

# ════════════════════════════════════════════════════════════
#  API — Health Profile
# ════════════════════════════════════════════════════════════
@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    try:
        data = request.get_json()
        result = calculate_health(data)
        diet_data = build_diet_plan(data)

        conn = get_db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO users (name,age,gender,weight,height,country,pa,stress,water,sleep,family,habits,bmi,risk,diseases)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            result["name"], result["age"], result["gender"],
            result["weight"], result["height"], result["country"],
            result["pa"], result["stress"], result["water"], result["sleep"],
            json.dumps(result["family"]), json.dumps(result["habits"]),
            result["bmi"], result["risk"], json.dumps(result["diseases"])
        ))
        user_id = c.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "user_id": user_id,
            "profile": result,
            "diet_plan": diet_data
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/profile/<int:user_id>", methods=["GET"])
def api_get_profile(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"success": False, "error": "User not found"}), 404

    profile = dict(row)
    profile["family"]   = json.loads(profile["family"])
    profile["habits"]   = json.loads(profile["habits"])
    profile["diseases"] = json.loads(profile["diseases"])
    diet_data = build_diet_plan(profile)
    return jsonify({"success": True, "profile": profile, "diet_plan": diet_data})

# ════════════════════════════════════════════════════════════
#  API — Diary
# ════════════════════════════════════════════════════════════
@app.route("/api/diary/<int:user_id>", methods=["GET"])
def api_get_diary(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM diary WHERE user_id=? ORDER BY created_at DESC", (user_id,)
    ).fetchall()
    conn.close()
    return jsonify({"success": True, "entries": [dict(r) for r in rows]})

@app.route("/api/diary/<int:user_id>", methods=["POST"])
def api_add_diary(user_id):
    data = request.get_json()
    text = data.get("text", "").strip()
    mood = data.get("mood", "😊")
    if not text:
        return jsonify({"success": False, "error": "Empty entry"}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO diary (user_id,text,mood) VALUES (?,?,?)",
        (user_id, text, mood)
    )
    entry_id = c.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM diary WHERE id=?", (entry_id,)).fetchone()
    conn.close()
    return jsonify({"success": True, "entry": dict(row)})

@app.route("/api/diary/entry/<int:entry_id>", methods=["DELETE"])
def api_delete_diary(entry_id):
    conn = get_db()
    conn.execute("DELETE FROM diary WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# ════════════════════════════════════════════════════════════
#  API — Streak
# ════════════════════════════════════════════════════════════
@app.route("/api/streak/<int:user_id>", methods=["GET"])
def api_get_streak(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT day FROM streaks WHERE user_id=? ORDER BY day DESC", (user_id,)
    ).fetchall()
    conn.close()
    days = [r["day"] for r in rows]

    # Calculate current streak
    streak = 0
    check = date.today()
    while check.isoformat() in days:
        streak += 1
        check -= timedelta(days=1)

    # Last 7 days for calendar
    calendar = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        calendar.append({
            "date":  d.isoformat(),
            "day":   d.day,
            "done":  d.isoformat() in days,
            "today": i == 0
        })

    return jsonify({"success": True, "streak": streak, "days": days, "calendar": calendar})

@app.route("/api/streak/<int:user_id>/complete", methods=["POST"])
def api_complete_day(user_id):
    today = date.today().isoformat()
    conn = get_db()
    try:
        conn.execute("INSERT INTO streaks (user_id,day) VALUES (?,?)", (user_id, today))
        conn.commit()
        msg = "Day marked complete! 🔥"
    except sqlite3.IntegrityError:
        msg = "Already marked today complete!"
    conn.close()
    return jsonify({"success": True, "message": msg})

# ════════════════════════════════════════════════════════════
#  API — Tasks
# ════════════════════════════════════════════════════════════
@app.route("/api/tasks/<int:user_id>", methods=["GET"])
def api_get_tasks(user_id):
    today = date.today().isoformat()
    conn = get_db()
    row = conn.execute(
        "SELECT tasks_json FROM tasks WHERE user_id=? AND day=?", (user_id, today)
    ).fetchone()
    conn.close()

    if row:
        tasks = json.loads(row["tasks_json"])
    else:
        tasks = DEFAULT_TASKS.copy()
        conn = get_db()
        conn.execute(
            "INSERT OR IGNORE INTO tasks (user_id,day,tasks_json) VALUES (?,?,?)",
            (user_id, today, json.dumps(tasks))
        )
        conn.commit()
        conn.close()

    return jsonify({"success": True, "tasks": tasks, "day": today})

@app.route("/api/tasks/<int:user_id>", methods=["PUT"])
def api_update_tasks(user_id):
    today = date.today().isoformat()
    data  = request.get_json()
    tasks = data.get("tasks", [])

    conn = get_db()
    conn.execute("""
        INSERT INTO tasks (user_id,day,tasks_json) VALUES (?,?,?)
        ON CONFLICT(user_id,day) DO UPDATE SET tasks_json=excluded.tasks_json
    """, (user_id, today, json.dumps(tasks)))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# ════════════════════════════════════════════════════════════
#  API — Stats
# ════════════════════════════════════════════════════════════
@app.route("/api/stats/<int:user_id>", methods=["GET"])
def api_stats(user_id):
    conn = get_db()
    diary_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM diary WHERE user_id=?", (user_id,)
    ).fetchone()["cnt"]

    streak_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM streaks WHERE user_id=?", (user_id,)
    ).fetchone()["cnt"]

    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()

    return jsonify({
        "success": True,
        "diary_entries": diary_count,
        "total_streak_days": streak_count,
        "bmi": user["bmi"] if user else None,
        "risk": user["risk"] if user else None,
    })

# ════════════════════════════════════════════════════════════
#  Boot
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    with app.app_context():
        init_db()

    print("🔥 App Starting...")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)



