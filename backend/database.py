import sqlite3
import uuid
import json
from datetime import datetime, timedelta
import random

DB_PATH = "disaster.db"

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # ── SOS Requests ──────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS sos_requests (
        sos_id        TEXT PRIMARY KEY,
        source_type   TEXT NOT NULL CHECK(source_type IN ('app','sms','missed_call','volunteer')),
        phone         TEXT,
        lat           REAL,
        lon           REAL,
        gps_accuracy  REAL,
        approx_loc    TEXT,
        people_count  INTEGER DEFAULT 1,
        emergency_type TEXT CHECK(emergency_type IN ('medical','flood','trapped','elderly','shelter','other','unknown')),
        status        TEXT DEFAULT 'pending' CHECK(status IN ('pending','assigned','in_progress','rescued','closed')),
        priority_score INTEGER DEFAULT 0,
        assigned_mission TEXT,
        raw_message   TEXT,
        created_at    TEXT,
        updated_at    TEXT
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sos_priority ON sos_requests(priority_score DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sos_status  ON sos_requests(status)")

    # ── Responders ────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS responders (
        id                  TEXT PRIMARY KEY,
        name                TEXT NOT NULL,
        type                TEXT CHECK(type IN ('boat','medical','volunteer','ambulance','helicopter','logistics','fire')),
        tier                TEXT DEFAULT 'local_volunteer' CHECK(tier IN ('government','ngo','certified_volunteer','local_volunteer')),
        trust_score         INTEGER DEFAULT 40,
        skills              TEXT DEFAULT '[]',
        equipment           TEXT DEFAULT '[]',
        vehicle_type        TEXT,
        lat                 REAL,
        lon                 REAL,
        gps_accuracy        REAL,
        phone               TEXT,
        status              TEXT DEFAULT 'available' CHECK(status IN ('available','busy','offline')),
        verification_status TEXT DEFAULT 'approved' CHECK(verification_status IN ('pending','approved','rejected')),
        district            TEXT DEFAULT 'Chennai',
        last_seen           TEXT,
        created_at          TEXT,
        updated_at          TEXT,
        department          TEXT,
        team_leader_name    TEXT,
        team_size           INTEGER,
        operating_radius    REAL,
        registration_number TEXT,
        metadata            TEXT DEFAULT '{}'
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_resp_status ON responders(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_resp_tier   ON responders(tier)")

    # ── Missions ──────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS missions (
        id               TEXT PRIMARY KEY,
        sos_id           TEXT,
        responder_id     TEXT,
        team_ids         TEXT DEFAULT '[]',
        type             TEXT,
        status           TEXT DEFAULT 'created' CHECK(status IN (
            'created','assigned','accepted','en_route','on_site',
            'rescue_in_progress','completed','cancelled'
        )),
        notes            TEXT,
        people_rescued   INTEGER DEFAULT 0,
        backup_requested INTEGER DEFAULT 0,
        created_at       TEXT,
        assigned_at      TEXT,
        completed_at     TEXT,
        updated_at       TEXT
    )""")

    # ── Support Requests ──────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS support_requests (
        id           TEXT PRIMARY KEY,
        mission_id   TEXT,
        responder_id TEXT,
        request_type TEXT CHECK(request_type IN ('boat','medical','fire','evacuation','logistics')),
        message      TEXT,
        status       TEXT DEFAULT 'pending' CHECK(status IN ('pending','dispatched','closed')),
        created_at   TEXT,
        updated_at   TEXT
    )""")

    # ── Shelters ──────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS shelters (
        id         TEXT PRIMARY KEY,
        name       TEXT,
        lat        REAL,
        lon        REAL,
        capacity   INTEGER,
        occupancy  INTEGER DEFAULT 0,
        district   TEXT DEFAULT 'Chennai',
        facilities TEXT,
        created_at TEXT
    )""")

    # ── Area Reports ──────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS area_reports (
        id           TEXT PRIMARY KEY,
        responder_id TEXT,
        lat          REAL,
        lon          REAL,
        condition    TEXT,
        water_level  TEXT CHECK(water_level IN ('none','ankle','knee','waist','chest','extreme')),
        road_blocked INTEGER DEFAULT 0,
        fire_detected INTEGER DEFAULT 0,
        building_damage TEXT CHECK(building_damage IN ('none','partial','severe')),
        boat_needed  INTEGER DEFAULT 0,
        notes        TEXT,
        district     TEXT DEFAULT 'Chennai',
        created_at   TEXT
    )""")

    # ── Alerts ────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id         TEXT PRIMARY KEY,
        type       TEXT,
        message    TEXT,
        level      TEXT CHECK(level IN ('info','warning','critical')),
        region     TEXT,
        dismissed  INTEGER DEFAULT 0,
        created_at TEXT
    )""")

    conn.commit()
    apply_migrations(conn)
    _seed(conn)
    conn.close()

def apply_migrations(conn):
    """Update schema for existing tables (ALTER TABLE if columns missing)."""
    c = conn.cursor()
    
    # ── Responders Migration ──────────────────────────────────────
    # Check for columns added in v3.1
    c.execute("PRAGMA table_info(responders)")
    columns = [row[1] for row in c.fetchall()]
    
    migrations = [
        ("department",          "TEXT"),
        ("team_leader_name",    "TEXT"),
        ("team_size",           "INTEGER"),
        ("operating_radius",    "REAL"),
        ("registration_number", "TEXT"),
        ("metadata",            "TEXT DEFAULT '{}'")
    ]
    
    for col_name, col_type in migrations:
        if col_name not in columns:
            print(f"Merging Schema: Adding column {col_name} to responders table...")
            c.execute(f"ALTER TABLE responders ADD COLUMN {col_name} {col_type}")
    
    conn.commit()


def reset_showcase(conn):
    """Wipe SOS + missions + support_requests for a clean demo. Keep responders."""
    c = conn.cursor()
    c.execute("DELETE FROM sos_requests")
    c.execute("DELETE FROM missions")
    c.execute("DELETE FROM support_requests")
    c.execute("DELETE FROM alerts")
    c.execute("UPDATE responders SET status='available', updated_at=?", (datetime.utcnow().isoformat(),))
    conn.commit()
    print("🔄 Showcase reset: SOS + missions cleared, responders kept available")


def _seed(conn):
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM responders").fetchone()[0] > 0:
        return

    now = datetime.utcnow()
    def ts(delta_minutes=0):
        return (now - timedelta(minutes=delta_minutes)).isoformat()

    BASE_LAT, BASE_LON = 13.0827, 80.2707

    def jitter(base, spread=0.08):
        return round(base + random.uniform(-spread, spread), 5)

    # ── Seed Responders (4 tiers) ──
    responders = [
        # Government (trust 100)
        ("NDRF Team Chennai",      "boat",       "government",          100, "9841001001", ["flood_rescue","swift_water"], ["boat","rescue_gear","medical_kit"], "Boat",        "Chennai North",    "approved"),
        ("Fire & Rescue Unit 1",   "fire",       "government",          100, "9841001002", ["fire_rescue","building_rescue"], ["rescue_gear","breathing_app"], "Truck",      "Adyar",            "approved"),
        ("Police Rescue Team",     "volunteer",  "government",          100, "9841001003", ["crowd_control","first_aid"], ["rescue_gear"],                  "Van",              "Chennai Central",  "approved"),
        # NGO (trust 80)
        ("Red Cross Team A",       "medical",    "ngo",                  80, "9841002001", ["first_aid","medical_training"], ["ambulance","medical_kit"],    "Ambulance",        "Guindy",           "approved"),
        ("Red Cross Boat Team",    "boat",       "ngo",                  80, "9841002002", ["boat_driving","swimming"],    ["boat","life_jackets"],          "Boat",             "Velachery",        "approved"),
        ("Mercy NGO Logistics",    "logistics",  "ngo",                  80, "9841002003", ["logistics","food_distribution"], ["van","food_supplies"],       "Van",              "Koyambedu",        "approved"),
        # Certified Volunteers (trust 60)
        ("Kumar (Certified)",      "volunteer",  "certified_volunteer",  60, "9841003001", ["swimming","first_aid"],       ["bike"],                         "Bike",             "Sholinganallur",   "approved"),
        ("Priya (Certified Med)",  "medical",    "certified_volunteer",  60, "9841003002", ["medical_training","first_aid"],["car"],                         "Car",              "Chromepet",        "approved"),
        ("Rajan (Boat Expert)",    "boat",       "certified_volunteer",  60, "9841003003", ["boat_driving","swimming"],    ["boat"],                         "Boat (12-seater)", "Manali",           "approved"),
        ("Ambulance Volunteer 1",  "ambulance",  "certified_volunteer",  60, "9841003004", ["first_aid","driving"],        ["ambulance"],                    "Ambulance",        "Perambur",         "approved"),
        # Local Volunteers (trust 40)
        ("Murugan (Local)",        "volunteer",  "local_volunteer",      40, "9841004001", ["helper"],                     ["bike"],                         "Bike",             "Avadi",            "approved"),
        ("Selvi (Local)",          "volunteer",  "local_volunteer",      40, "9841004002", ["swimmer","helper"],           [],                               None,               "Tambaram",         "approved"),
        ("Venkat (Boat Owner)",    "boat",       "local_volunteer",      40, "9841004003", ["boat_driver"],                ["boat"],                         "Boat (6-seater)",  "Royapuram",        "approved"),
        # Specialist
        ("Helicopter Unit 1",      "helicopter", "government",          100, "9841005001", ["aerial_rescue","hoisting"],   ["helicopter"],                   "Helicopter",       "Chennai Airport",  "approved"),
        ("Medical Van 3",          "medical",    "ngo",                  80, "9841006001", ["medical_training","emergency_care"], ["ambulance","icu_kit"],   "Ambulance",        "Anna Nagar",       "approved"),
        ("Kanyakumari Boat Team",   "boat",       "ngo",                  80, "9841007001", ["sea_rescue","swimming"],        ["boat","life_jackets"],          "Boat",             "Kanyakumari",      "approved"),
        ("Madurai Medical Unit",    "medical",    "government",          100, "9841008001", ["emergency_care"],               ["ambulance","first_aid"],        "Ambulance",        "Madurai",          "approved"),
        ("Coimbatore Rescue 1",     "volunteer",  "certified_volunteer",  60, "9841009001", ["climbing","helper"],           ["bike"],                         "Bike",             "Coimbatore",       "approved"),
    ]

    for name, rtype, tier, trust, phone, skills, equip, vehicle, district, vstatus in responders:
        rid = str(uuid.uuid4())
        c.execute("""INSERT INTO responders
            (id,name,type,tier,trust_score,skills,equipment,vehicle_type,lat,lon,gps_accuracy,phone,status,verification_status,district,last_seen,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rid, name, rtype, tier, trust,
             json.dumps(skills), json.dumps(equip), vehicle,
             jitter(BASE_LAT), jitter(BASE_LON), round(random.uniform(8, 35), 1),
             phone, "available", vstatus, district, ts(), ts(random.randint(1,5)), ts()))

    # ── Seed SOS ──
    sos_data = [
        ("app",         "9841100001", 13.0456, 80.2134, 4, "flood",   "pending",      90, 8.5),
        ("sms",         "9841100002", 13.0612, 80.2489, 2, "medical", "pending",      70, None),
        ("volunteer",   "9841100003", 13.1023, 80.2901, 6, "trapped", "assigned",    100, 12.3),
        ("app",         "9841100004", 13.0789, 80.2345, 1, "elderly", "in_progress",  60, 6.1),
        ("missed_call", "9841100005", 13.0234, 80.2678, 3, "flood",   "pending",      80, None),
        ("app",         "9841100006", 13.0567, 80.2901, 5, "medical", "rescued",      85, 9.2),
        ("sms",         "9841100007", 13.0890, 80.2123, 2, "trapped", "closed",       75, None),
        ("app",         "9841100008", 13.0345, 80.2567, 3, "flood",   "pending",      95, 15.0),
    ]
    sos_ids = []
    for src, phone, lat, lon, pcount, etype, status, score, acc in sos_data:
        sid = str(uuid.uuid4())
        sos_ids.append(sid)
        c.execute("""INSERT INTO sos_requests
            (sos_id,source_type,phone,lat,lon,gps_accuracy,approx_loc,people_count,emergency_type,status,priority_score,assigned_mission,raw_message,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (sid, src, phone, lat, lon, acc,
             f"Near {lat:.2f},{lon:.2f}", pcount, etype, status, score,
             None, None, ts(random.randint(5,90)), ts()))

    # ── Seed Missions ──
    resp_ids = [r[0] for r in c.execute("SELECT id FROM responders LIMIT 5").fetchall()]
    missions_seed = [
        (sos_ids[2], resp_ids[0], "boat rescue",    "assigned",             "[]"),
        (sos_ids[3], resp_ids[1], "medical rescue", "en_route",             "[]"),
        (sos_ids[5], resp_ids[2], "evacuation",     "completed",            "[]"),
    ]
    for sid, rid, mtype, mstatus, team_ids in missions_seed:
        mid = str(uuid.uuid4())
        completed = ts(5) if mstatus == "completed" else None
        c.execute("""INSERT INTO missions
            (id,sos_id,responder_id,team_ids,type,status,notes,people_rescued,backup_requested,created_at,assigned_at,completed_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (mid, sid, rid, team_ids, mtype, mstatus, None, 0, 0, ts(30), ts(25), completed, ts()))
        # Mark responder busy if not completed
        if mstatus not in ("completed", "cancelled"):
            c.execute("UPDATE responders SET status='busy' WHERE id=?", (rid,))

    # ── Seed Shelters ──
    shelters = [
        ("Chennai Relief Camp A",         13.0456, 80.2345, 500, 312, "Chennai North", "Food,Water,Medical"),
        ("School Shelter Adyar",          13.0012, 80.2567, 300, 198, "Adyar",         "Food,Water"),
        ("Community Hall Velachery",      12.9815, 80.2189, 400, 401, "Velachery",     "Food,Water,Medical,Power"),
        ("Government School Tambaram",    12.9234, 80.1134, 600, 245, "Tambaram",      "Food,Water"),
        ("Sports Complex Guindy",         13.0089, 80.2012, 800, 550, "Guindy",        "Food,Water,Medical,Power"),
    ]
    for name, lat, lon, cap, occ, dist, fac in shelters:
        c.execute("INSERT INTO shelters VALUES (?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), name, lat, lon, cap, occ, dist, fac, ts()))

    # ── Seed Area Reports ──
    rids2 = [r[0] for r in c.execute("SELECT id FROM responders LIMIT 5").fetchall()]
    reports = [
        (rids2[0], 13.0456, 80.2134, "Heavy flooding, many trapped", "chest",   1, 0, "partial", 1, "Need boats urgently"),
        (rids2[1], 13.0612, 80.2489, "Road blocked by debris",       "knee",    1, 0, "none",    0, "Alternate route via NH-32"),
        (rids2[2], 13.0789, 80.2345, "Moderate flooding",            "ankle",   0, 0, "none",    0, "Passable on foot"),
        (rids2[3], 13.1023, 80.2901, "Severe flooding",              "waist",   1, 0, "partial", 1, "Boat only zone"),
        (rids2[4], 13.0234, 80.2678, "Bridge collapsed",             "extreme", 1, 0, "severe",  1, "Area inaccessible"),
    ]
    for rid, lat, lon, cond, wl, rb, fd, bd, bn, notes in reports:
        c.execute("""INSERT INTO area_reports
            (id,responder_id,lat,lon,condition,water_level,road_blocked,fire_detected,building_damage,boat_needed,notes,district,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4()), rid, lat, lon, cond, wl, rb, fd, bd, bn, notes, "Chennai",
             ts(random.randint(10,60))))

    # ── Seed Alerts ──
    alerts = [
        ("cluster",  "High SOS cluster detected in Velachery zone",       "critical", "Velachery"),
        ("resource", "No rescue team available in Tambaram area",          "warning",  "Tambaram"),
        ("flood",    "Water level rising in Adyar river basin",            "critical", "Adyar"),
        ("shelter",  "Velachery Community Hall shelter capacity exceeded", "warning",  "Velachery"),
        ("weather",  "Heavy rainfall expected for next 6 hours",          "info",     "All Districts"),
    ]
    for atype, msg, level, region in alerts:
        c.execute("INSERT INTO alerts VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), atype, msg, level, region, 0, ts(random.randint(1,30))))

    conn.commit()
    print("✅ Database seeded with 4-tier Chennai flood scenario data")
