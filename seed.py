"""
seed.py — populate the UniShare DB with realistic test data.
Run once:  python seed.py
Re-seed:   python seed.py --reset   (wipes and re-creates everything)
"""

import sys
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from database import get_db, init_db, DATABASE

# ─────────────────────────────────────────────────────────────────
# Raw data
# ─────────────────────────────────────────────────────────────────

USERS = [
    ("Jessica", "Thompson", "23001001@student.uwa.edu.au", "password123", 2450, "Campus Legend"),
    ("Liam",    "Nguyen",   "23001002@student.uwa.edu.au", "password123", 1820, "Campus Legend"),
    ("Priya",   "Sharma",   "23001003@student.uwa.edu.au", "password123",  870, "Hustler"),
    ("Callum",  "Reid",     "23001004@student.uwa.edu.au", "password123",  640, "Hustler"),
    ("Mei",     "Chen",     "23001005@student.uwa.edu.au", "password123",  410, "Newbie"),
    ("Oliver",  "Walsh",    "23001006@student.uwa.edu.au", "password123",  290, "Newbie"),
    ("Aisha",   "Malik",    "23001007@student.uwa.edu.au", "password123",  150, "Newbie"),
    ("Tom",     "Barker",   "23001008@student.uwa.edu.au", "password123",   80, "Newbie"),
]

LISTINGS = [
    # (seller_index, title, unit_code, price, condition, description)
    (0, "Agile Web Development 5th Ed.",         "CITS3403", 45.00, "Good",      "A few highlights in chapter 3, otherwise great condition."),
    (0, "Introduction to Algorithms (CLRS)",     "CITS2200", 60.00, "Like new",  "Used for one semester, no writing."),
    (1, "Computer Networks: A Top-Down Approach","CITS3002", 38.00, "Acceptable","Cover slightly bent, all pages intact."),
    (1, "Operating System Concepts (Dinosaur)",  "CITS2002", 42.00, "Good",      "Some sticky notes but easily removed."),
    (2, "Calculus Early Transcendentals 8th Ed.","MATH1012", 30.00, "Good",      "Pencil workings in margins, easy to erase."),
    (2, "Linear Algebra and Its Applications",   "MATH2402", 25.00, "Like new",  "Barely opened — withdrew from unit."),
    (3, "Business Statistics",                   "STAT2401", 20.00, "Acceptable","Spine worn but readable throughout."),
    (3, "Database System Concepts 7th Ed.",      "CITS3200", 50.00, "New",       "Bought the wrong edition, never opened."),
    (4, "Engineering Mathematics",               "MATH1011", 35.00, "Good",      "Good condition, a few folded page corners."),
    (5, "Molecular Cell Biology 8th Ed.",        "BIOC2002", 55.00, "Like new",  "International edition — same content, smaller price."),
    (6, "Principles of Marketing",               "MKTG1100", 22.00, "Acceptable","Some yellow highlighting throughout."),
    (7, "Financial Accounting",                  "ACCT1101", 28.00, "Good",      "Previous owner's name on inside cover."),
]

NOTES = [
    # (author_index, title, unit_code, semester, description, upvotes)
    (0, "CITS3403 Complete Lecture Summary S1",   "CITS3403", "S1 2025", "All 12 weeks condensed into 40 pages. Covers Flask, JS, SQL, testing.", 47),
    (0, "CITS3403 Final Exam Cheat Sheet",        "CITS3403", "S1 2025", "One-page A4 summary allowed in exam. Key patterns and gotchas.", 38),
    (1, "CITS2200 Algorithm Analysis Notes",      "CITS2200", "S1 2025", "Big-O, sorting algorithms, graph traversals with worked examples.", 29),
    (1, "CITS2002 Systems Programming Guide",     "CITS2002", "S2 2024", "C pointers, memory management, process management — with diagrams.", 24),
    (2, "MATH1012 Calculus Week 1–6 Notes",       "MATH1012", "S1 2025", "Limits, derivatives, integrals — hand-written scans, very clear.", 19),
    (2, "MATH2402 Linear Algebra Summary",        "MATH2402", "S1 2025", "Eigenvalues, vector spaces, matrix decompositions.", 15),
    (3, "STAT2401 R Code Cheatsheet",             "STAT2401", "S2 2024", "All the R snippets you need for the practicals in one file.", 33),
    (4, "CITS3003 Graphics OpenGL Notes",         "CITS3003", "S1 2025", "Week-by-week notes covering shaders, transformations, lighting.", 11),
    (5, "BIOC2002 Protein Synthesis Summary",     "BIOC2002", "S1 2025", "Transcription → translation, with annotated diagrams.", 8),
    (6, "MKTG1100 Marketing Mix Notes",           "MKTG1100", "S2 2024", "4Ps framework, case studies, and common exam questions.", 6),
]

SESSIONS = [
    # (host_index, title, unit_code, location, days_from_now, max_att, description)
    (0, "CITS3403 Project 2 Sprint Planning",  "CITS3403", "Reid Library Level 2, Bay 14",  3,  6, "Going through the marking rubric and splitting tasks for the final sprint."),
    (1, "CITS2200 Exam Prep — Algorithms",     "CITS2200", "Computer Science Building G.14",  5,  8, "Working through past papers together. Bring your notes."),
    (2, "MATH1012 Calculus Study Group",       "MATH1012", "Barry J Marshall Library",        2, 10, "Weekly study group, open to anyone struggling with integration."),
    (3, "CITS2002 Systems Programming Help",   "CITS2002", "Reid Library Level 3",            7,  5, "Helping with the C assignment — pointers and file I/O."),
    (4, "STAT2401 R Practical Walkthrough",    "STAT2401", "Education Building G.21",         1,  12, "Running through the week 8 practical before the due date."),
    (0, "CITS3403 Flask Backend Q&A",          "CITS3403", "Online — Discord link in bio",    4,  20, "Open session — ask anything about the Flask backend and SQLite schema."),
]

BOUNTIES = [
    # (poster_index, title, unit_code, reward, description)
    (0, "Need CITS3403 project partner for final sprint",     "CITS3403", 0,     "Looking for one more person to join our group. We have frontend done, need backend help."),
    (1, "Past exam papers for CITS2200",                     "CITS2200", 10.00, "Will pay $10 for any past CITS2200 exam papers from 2022 or earlier."),
    (2, "Tutor needed for MATH1012 — $30/hr",                "MATH1012", 30.00, "Struggling with integration techniques. Need 2–3 sessions before the exam."),
    (3, "Anyone selling a CITS3002 textbook?",               "CITS3002", 0,     "Need the Tanenbaum networking book ASAP. Can pick up anywhere on campus."),
    (4, "Proofread my ENGL1000 essay — $15",                 "ENGL1000", 15.00, "1500 word essay on postcolonial literature. Need feedback within 48 hours."),
    (5, "Lost UWA student card — reward for return",         "",         20.00, "Lost near Guild Village on Tuesday. Name on card. No questions asked."),
    (6, "Looking for ACCT1101 study notes",                  "ACCT1101", 5.00,  "Specifically need notes on the double-entry bookkeeping lectures."),
]

# RSVPs: (session_index, [user_indices who RSVP'd])
RSVPS = [
    (0, [1, 2, 3]),
    (1, [0, 3, 4, 5]),
    (2, [0, 1, 5, 6, 7]),
    (3, [0, 2]),
    (4, [1, 2, 3, 6]),
    (5, [1, 2, 3, 4, 5, 6, 7]),
]

# Saved listings: (user_index, [listing_indices])
SAVED = [
    (2, [0, 3, 7]),
    (3, [1, 4]),
    (4, [0, 2, 5]),
    (5, [7, 8]),
]

# Ratings: (rater_index, rated_index, listing_index, score, comment)
RATINGS = [
    (2, 0, 0, 5, "Book was exactly as described, super fast reply!"),
    (3, 0, 1, 5, "Jess is a legend, smooth transaction."),
    (4, 1, 2, 4, "Good condition, took a day to reply but all good."),
    (5, 1, 3, 5, "Perfect, met on campus, no issues."),
    (0, 2, 4, 4, "Minor pencil marks but she was upfront about it."),
    (1, 3, 7, 5, "Brand new as advertised!"),
]


# ─────────────────────────────────────────────────────────────────
# Seeder
# ─────────────────────────────────────────────────────────────────

def reset_db():
    conn = sqlite3.connect(DATABASE)
    conn.executescript("""
        DROP TABLE IF EXISTS ratings;
        DROP TABLE IF EXISTS saved_listings;
        DROP TABLE IF EXISTS session_rsvps;
        DROP TABLE IF EXISTS bounties;
        DROP TABLE IF EXISTS sessions;
        DROP TABLE IF EXISTS notes;
        DROP TABLE IF EXISTS listings;
        DROP TABLE IF EXISTS users;
    """)
    conn.commit()
    conn.close()
    print("Database wiped.")


def seed():
    db = get_db()
    now = datetime.now()

    # ── Users
    user_ids = []
    for first, last, email, pw, xp, rank in USERS:
        cur = db.execute(
            "INSERT INTO users (first_name, last_name, email, password_hash, xp, rank) VALUES (?,?,?,?,?,?)",
            (first, last, email, generate_password_hash(pw), xp, rank)
        )
        user_ids.append(cur.lastrowid)
    print(f"  ✓ {len(user_ids)} users")

    # ── Listings
    listing_ids = []
    for seller_i, title, unit, price, cond, desc in LISTINGS:
        cur = db.execute(
            "INSERT INTO listings (seller_id, title, unit_code, price, condition, description) VALUES (?,?,?,?,?,?)",
            (user_ids[seller_i], title, unit, price, cond, desc)
        )
        listing_ids.append(cur.lastrowid)
    print(f"  ✓ {len(listing_ids)} listings")

    # ── Notes
    for author_i, title, unit, sem, desc, upvotes in NOTES:
        db.execute(
            "INSERT INTO notes (author_id, title, unit_code, semester, description, upvotes) VALUES (?,?,?,?,?,?)",
            (user_ids[author_i], title, unit, sem, desc, upvotes)
        )
    print(f"  ✓ {len(NOTES)} notes")

    # ── Sessions
    session_ids = []
    for host_i, title, unit, location, days, max_att, desc in SESSIONS:
        session_date = (now + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
        cur = db.execute(
            "INSERT INTO sessions (host_id, title, unit_code, location, session_date, max_attendees, description) VALUES (?,?,?,?,?,?,?)",
            (user_ids[host_i], title, unit, location, session_date, max_att, desc)
        )
        session_ids.append(cur.lastrowid)
    print(f"  ✓ {len(session_ids)} sessions")

    # ── RSVPs
    rsvp_count = 0
    for sess_i, user_indices in RSVPS:
        for user_i in user_indices:
            try:
                db.execute(
                    "INSERT INTO session_rsvps (session_id, user_id) VALUES (?,?)",
                    (session_ids[sess_i], user_ids[user_i])
                )
                rsvp_count += 1
            except Exception:
                pass
    print(f"  ✓ {rsvp_count} RSVPs")

    # ── Bounties
    for poster_i, title, unit, reward, desc in BOUNTIES:
        db.execute(
            "INSERT INTO bounties (poster_id, title, unit_code, reward, description) VALUES (?,?,?,?,?)",
            (user_ids[poster_i], title, unit or None, reward, desc)
        )
    print(f"  ✓ {len(BOUNTIES)} bounties")

    # ── Saved listings
    saved_count = 0
    for user_i, listing_indices in SAVED:
        for l_i in listing_indices:
            try:
                db.execute(
                    "INSERT INTO saved_listings (user_id, listing_id) VALUES (?,?)",
                    (user_ids[user_i], listing_ids[l_i])
                )
                saved_count += 1
            except Exception:
                pass
    print(f"  ✓ {saved_count} saved listings")

    # ── Ratings
    for rater_i, rated_i, listing_i, score, comment in RATINGS:
        db.execute(
            "INSERT INTO ratings (rater_id, rated_id, listing_id, score, comment) VALUES (?,?,?,?,?)",
            (user_ids[rater_i], user_ids[rated_i], listing_ids[listing_i], score, comment)
        )
        db.execute(
            "UPDATE users SET rating_sum = rating_sum + ?, rating_count = rating_count + 1 WHERE id = ?",
            (score, user_ids[rated_i])
        )
    print(f"  ✓ {len(RATINGS)} ratings")

    db.commit()
    db.close()


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if '--reset' in sys.argv:
        reset_db()

    init_db()
    print("Seeding database...")
    seed()
    print("\nDone! Log in with any of these accounts (password: password123):")
    print("  jessica  →  23001001@student.uwa.edu.au  (Campus Legend, 2450 XP)")
    print("  liam     →  23001002@student.uwa.edu.au  (Campus Legend, 1820 XP)")
    print("  priya    →  23001003@student.uwa.edu.au  (Hustler, 870 XP)")
    print("  tom      →  23001008@student.uwa.edu.au  (Newbie, 80 XP)")