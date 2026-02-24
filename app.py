
import os
from datetime import datetime, date

from flask import Flask, request, redirect, url_for, render_template_string
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///life_rpg.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024  # 6MB
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# MODELS
class Quest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    xp = db.Column(db.Integer, nullable=False, default=10)

    # NEW
    category = db.Column(db.String(32), nullable=False, default="Hobbies")  
    is_workout = db.Column(db.Boolean, nullable=False, default=False)

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quest_id = db.Column(db.Integer, db.ForeignKey("quest.id"), nullable=False)
    ts = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False, default="")

class FitnessPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(10), nullable=False, unique=True)  # YYYY-MM-DD
    filename = db.Column(db.String(255), nullable=False)
    ts = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


# HELPERS
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_note(key: str, default: str = "") -> Note:
    n = Note.query.filter_by(key=key).first()
    if not n:
        n = Note(key=key, value=default)
        db.session.add(n)
        db.session.commit()
    return n

def total_xp() -> int:
    # sum XP over all logs (join quest)
    rows = db.session.query(Log, Quest).join(Quest, Log.quest_id == Quest.id).all()
    return sum(q.xp for _, q in rows)

def level_from_xp(xp: int) -> tuple[int, int]:
    # simple curve: next_level_xp = level*100
    level = 1
    remaining = xp
    while remaining >= level * 100:
        remaining -= level * 100
        level += 1
    next_req = level * 100
    return level, next_req - remaining

def today_count(quest_id: int) -> int:
    start = datetime.combine(date.today(), datetime.min.time())
    end = datetime.combine(date.today(), datetime.max.time())
    return Log.query.filter(Log.quest_id == quest_id, Log.ts >= start, Log.ts <= end).count()

# TEMPLATE
PAGE = """
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Life RPG</title>

  <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap" rel="stylesheet">

  <style>
    :root{
      --bg:#0d0d0d;
      --panel:#111;
      --neon:#39ff14;
      --cyan:#00ffff;
      --muted:#9aa0a6;
      --border: #2a2a2a;
    }

    *{ box-sizing:border-box; }

    body{
      margin: 28px auto;
      padding: 0 18px;
      max-width: min(1600px, 96vw);
      background: var(--bg);
      color: var(--neon);
      font-family: 'VT323', monospace;
      font-size: clamp(18px, 1.2vw, 24px);
    }

    .header{
      display:flex;
      align-items:flex-end;
      justify-content:space-between;
      gap:18px;
      flex-wrap:wrap;
      margin-bottom:18px;
      max width: 100%;
    }

    .logo{
      width: clamp(160px, 40vw, 320px);
      height:auto;
      display:block;
      image-rendering: pixelated;
    }

    .tagline{
      color: var(--muted);
      max-width: 420px;
      line-height: 1.2;
    }

    .grid{
      display:grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 20px;
      align-items: stretch;
    }

    .card{
      background: var(--panel);
      border: 2px solid var(--neon);
      border-radius: 14px;
      padding: 16px;
      box-shadow: 0 0 14px rgba(57,255,20,0.18);
      min-height: clamp(200px, 25vh, 400px);
    }

    h3{
      margin: 0 0 10px 0;
      font-family: 'Press Start 2P', cursive;
      font-size: 14px;
      color: var(--cyan);
      line-height: 1.3;
    }

    p{ margin: 8px 0; }

    .pill{
      display:inline-block;
      padding: 2px 10px;
      border: 1px solid var(--cyan);
      border-radius: 999px;
      color: var(--cyan);
      font-size: 16px;
      margin-left: 8px;
    }

    .quest{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap: 12px;
      padding: 12px 0;
      border-bottom: 1px solid #222;
    }

    .quest:last-child{ border-bottom:none; }

    button{
      background:#000;
      color: var(--neon);
      border: 2px solid var(--neon);
      padding: 8px 12px;
      border-radius: 12px;
      font-family: 'VT323', monospace;
      font-size: 20px;
      cursor:pointer;
      transition: 0.15s ease;
      white-space:nowrap;
    }

    button:hover{
      background: var(--neon);
      color:#000;
      box-shadow: 0 0 12px rgba(57,255,20,0.6);
    }

    input, textarea{
      width:100%;
      background:#000;
      color: var(--cyan);
      border: 2px solid var(--cyan);
      border-radius: 12px;
      padding: 10px 12px;
      font-family: 'VT323', monospace;
      font-size: 20px;
      outline:none;
    }

    textarea{ height: 140px; resize: vertical; }

    label{ color: var(--muted); display:block; margin: 10px 0 6px; }

    hr{ border: none; border-top: 1px solid #222; margin: 18px 0; }

    .span-2{ grid-column: span 2; }
    @media (max-width: 900px){
      .span-2{ grid-column: span 1; }
    }

    /* Make Quick Quests not explode the page */
    .quests-list{
      max-height: 420px;
      overflow:auto;
      padding-right: 6px;
    }
    .quests-list::-webkit-scrollbar{ width: 10px; }
    .quests-list::-webkit-scrollbar-thumb{ background:#1f1f1f; border-radius:999px; border:1px solid #333; }

    @media (max-width: 980px){
      .grid{ grid-template-columns: repeat(2, minmax(240px, 1fr)); }
      .span-2{ grid-column: span 2; }
    }
    @media (max-width: 640px){
      body{ margin:16px; }
      .grid{ grid-template-columns: 1fr; }
      .span-2, .span-1{ grid-column: span 1; }
      .logo{ width: 100%; max-width: 520px; }
    }
  </style>
</head>

<body>
  <div class="header">
    <div>
      <img class="logo" src="{{ url_for('static', filename='logo.png') }}" alt="Life RPG">
      <div class="tagline">Local. Private. Built for bad days.</div>
    </div>
  </div>

  <div class="grid">
    <div class="card span-1">
      <h3>Status</h3>
      <p><b>Level:</b> {{ level }}</p>
      <p><b>Total XP:</b> {{ xp }}</p>
      <p><b>XP to next level:</b> {{ to_next }}</p>
    </div>

    <div class="card span-2">
      <h3>Pain Snapshot</h3>
      <form method="post" action="{{ url_for('save_snapshot') }}">
        <textarea name="snapshot" placeholder="Write what today felt like. Keep it raw, short, real.">{{ snapshot }}</textarea>
        <div style="margin-top:10px;">
          <button type="submit">Save snapshot</button>
        </div>
      </form>
    </div>

    <div class="card span-2">
      <h3>Fitness Journey</h3>

      {% if latest_photo %}
        <div style="margin:10px 0; color:var(--muted);">Latest photo:</div>
        <img src="{{ url_for('static', filename='uploads/' + latest_photo.filename) }}" style="max-width:100%; border-radius:12px; border:1px solid #222;">
      {% endif %}

      <div class="quests-list" style="margin-top:12px;">
        {% for q in grouped["Fitness"] %}
        <div class="quest">
          <div>
            <div><b>{{ q.name }}</b><span class="pill">{{ q.xp }} XP</span></div>
            <div style="color:var(--muted)">Done today: {{ today_done[q.id] }}</div>
          </div>
          <form method="post" action="{{ url_for('do_quest', quest_id=q.id) }}">
            <button type="submit">Complete</button>
          </form>
        </div>
      {% endfor %}
    </div>

    <hr>

    <h3>Daily Photo</h3>

    {% if fitness_uploaded %}
      <div style="color:var(--cyan);">Uploaded today ✅</div>
    {% elif not fitness_unlock %}
      <div style="color:var(--muted);">Locked 🔒 Complete all workout quests to upload.</div>
    {% else %}
      <form method="post" action="{{ url_for('fitness_upload') }}" enctype="multipart/form-data">
        <input type="file" name="photo" accept="image/*" required>
        <div style="margin-top:10px;">
          <button type="submit">Upload today’s photo</button>
        </div>
      </form>
    {% endif %}
  </div>

    <div class="card span-1">
      <h3>Add Quest</h3>
      <form method="post" action="{{ url_for('add_quest') }}">
        <label>Name</label>
        <input name="name" placeholder="Skate 10 min, Football drills, Study 25 min..." required>

        <label>XP</label>
        <input name="xp" type="number" min="1" max="500" value="10" required>

        <div style="margin-top:10px;">
          <button type="submit">Add</button>
        </div>
      </form>

      <label>Category</label>
      <select name="category">
        <option>Fitness</option>
        <option>Food</option>
        <option selected>Hobbies</option>
        <option>Education</option>
      </select>

      <label style="display:flex; gap:10px; align-items:center; margin-top:10px;">
        <input type="checkbox" name="is_workout" value="1">
        Counts as workout (unlocks photo)
      </label>

      <hr>

      <h3>Starter pack</h3>
      <form method="post" action="{{ url_for('seed') }}">
        <button type="submit">Load default quests</button>
      </form>
    </div>
  </div>
</body>
</html>
"""


# ROUTES
@app.post("/fitness/upload")
def fitness_upload():
    today = date.today().isoformat()

    # Block if already uploaded today
    if FitnessPhoto.query.filter_by(day=today).first():
        return redirect(url_for("index"))

    # Check workouts completed today
    fitness_workouts = Quest.query.filter_by(category="Fitness", is_workout=True).all()
    all_done = all(today_count(q.id) > 0 for q in fitness_workouts) if fitness_workouts else False

    if not all_done:
        return redirect(url_for("index"))

    if "photo" not in request.files:
        return redirect(url_for("index"))

    file = request.files["photo"]
    if file.filename == "":
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        return redirect(url_for("index"))

    safe = secure_filename(file.filename)
    # store with date prefix to avoid collisions
    out_name = f"{today}_{safe}"
    out_path = os.path.join(app.config["UPLOAD_FOLDER"], out_name)
    file.save(out_path)

    db.session.add(FitnessPhoto(day=today, filename=out_name))
    db.session.commit()
    return redirect(url_for("index"))

@app.route("/")
def index():
    xp = total_xp()
    level, to_next = level_from_xp(xp)
    snapshot = get_note("snapshot", "").value

    quests = Quest.query.order_by(Quest.category.asc(), Quest.name.asc()).all()
    today_done = {q.id: today_count(q.id) for q in quests}

    # Group quests
    grouped = {"Fitness": [], "Food": [], "Hobbies": [], "Education": []}
    for q in quests:
        grouped.setdefault(q.category, []).append(q)

    # Fitness photo lock
    today = date.today().isoformat()
    fitness_uploaded = FitnessPhoto.query.filter_by(day=today).first()
    fitness_workouts = [q for q in grouped.get("Fitness", []) if q.is_workout]
    fitness_unlock = (len(fitness_workouts) > 0) and all(today_done[q.id] > 0 for q in fitness_workouts)

    # Show latest photo too
    latest_photo = FitnessPhoto.query.order_by(FitnessPhoto.day.desc()).first()

    return render_template_string(
        PAGE,
        xp=xp, level=level, to_next=to_next,
        snapshot=snapshot,
        grouped=grouped,
        today_done=today_done,
        fitness_unlock=fitness_unlock,
        fitness_uploaded=fitness_uploaded,
        latest_photo=latest_photo
    )

@app.post("/snapshot")
def save_snapshot():
    text = (request.form.get("snapshot") or "").strip()
    n = get_note("snapshot", "")
    n.value = text
    db.session.commit()
    return redirect(url_for("index"))

@app.post("/quest/add")
def add_quest():
    name = (request.form.get("name") or "").strip()
    xp = int(request.form.get("xp") or "10")
    category = (request.form.get("category") or "Hobbies").strip()
    is_workout = (request.form.get("is_workout") == "1")

    if name:
        existing = Quest.query.filter_by(name=name).first()
        if not existing:
            db.session.add(Quest(name=name, xp=xp, category=category, is_workout=is_workout))
            db.session.commit()
    return redirect(url_for("index"))

@app.post("/quest/<int:quest_id>/do")
def do_quest(quest_id: int):
    q = Quest.query.get_or_404(quest_id)
    db.session.add(Log(quest_id=q.id))
    db.session.commit()
    return redirect(url_for("index"))

@app.post("/seed")
def seed():
    defaults = [
      # Fitness (workouts that unlock photo)
      ("Workout 15 min", 20, "Fitness", True),
      ("Core / abs 10 min", 15, "Fitness", True),
      ("Stretch 8 min", 10, "Fitness", True),

      # Food
      ("Eat clean today", 15, "Food", False),
      ("Drink 2L water", 10, "Food", False),

      # Hobbies
      ("Skate 10 min", 20, "Hobbies", False),
      ("Football 20 min", 25, "Hobbies", False),

      # Education
      ("Study 25 min", 15, "Education", False),
      ("Apply for 1 job", 30, "Education", False),

    ]

    for name, xp, cat, is_workout in defaults:
      if not Quest.query.filter_by(name=name).first():
        db.session.add(Quest(name=name, xp=xp, category=cat, is_workout=is_workout))
    db.session.commit()
    return redirect(url_for("index"))

# MAIN
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        get_note("snapshot", "")
    app.run(host="127.0.0.1", port=5000, debug=True)
