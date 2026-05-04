"""
seed.py — populate the UniShare DB with realistic demo data.

Usage:
  python seed.py            # Add core seed data (skips if users already exist)
  python seed.py --reset    # Wipe all records and re-seed with core data
  python seed.py --full     # --reset + expanded dataset (more users/content)
"""

import sys
from datetime import datetime, timedelta, timezone

from app import create_app
from app.extensions import db
from app.models import (
    User, Listing, Note, StudySession, SessionRSVP,
    Bounty, SavedListing, Rating, Message, Post,
)

# ─────────────────────────────────────────────────────────────────
# Core seed data
# ─────────────────────────────────────────────────────────────────

USERS = [
    # (first, last, email, password, xp, rank, bio)
    ("Jessica", "Thompson", "23001001@student.uwa.edu.au", "password123", 2450, "Campus Legend",
     "Final year CompSci student. I love Flask and making things work. Always happy to help juniors."),
    ("Liam",    "Nguyen",   "23001002@student.uwa.edu.au", "password123", 1820, "Campus Legend",
     "CS + Maths double degree. Algorithm nerd. Happy to tutor — just message me."),
    ("Priya",   "Sharma",   "23001003@student.uwa.edu.au", "password123",  870, "Hustler",
     "MATH1012 survivor. Now paying it forward with study notes and group sessions."),
    ("Callum",  "Reid",     "23001004@student.uwa.edu.au", "password123",  640, "Hustler",
     "Systems programming enthusiast. C is life. Ask me about pointers."),
    ("Mei",     "Chen",     "23001005@student.uwa.edu.au", "password123",  410, "Newbie",
     "First year — still finding my feet. Stats and data science stream."),
    ("Oliver",  "Walsh",    "23001006@student.uwa.edu.au", "password123",  290, "Newbie",
     "Bio/Chem student. Looking for study buddies and affordable textbooks."),
    ("Aisha",   "Malik",    "23001007@student.uwa.edu.au", "password123",  150, "Newbie",
     "Marketing major. New to campus, loving it so far. Always down to collaborate."),
    ("Tom",     "Barker",   "23001008@student.uwa.edu.au", "password123",   80, "Newbie",
     "Accounting first year. Anyone selling ACCT1101 notes? Message me!"),
]

LISTINGS = [
    # (seller_idx, title, unit_code, price, condition, description)
    (0, "Agile Web Development 5th Ed.",          "CITS3403", 45.00, "Good",
     "A few highlights in chapter 3, otherwise great condition. Perfect for the project."),
    (0, "Introduction to Algorithms (CLRS)",      "CITS2200", 60.00, "Like new",
     "Used for one semester, no writing. The bible of algorithms."),
    (1, "Computer Networks: A Top-Down Approach", "CITS3002", 38.00, "Acceptable",
     "Cover slightly bent, all pages intact. Great for the networking units."),
    (1, "Operating System Concepts (Dinosaur)",   "CITS2002", 42.00, "Good",
     "Some sticky notes but easily removed. Really helped me understand processes."),
    (2, "Calculus Early Transcendentals 8th Ed.", "MATH1012", 30.00, "Good",
     "Pencil workings in margins, easy to erase. Brilliant reference for the exam."),
    (2, "Linear Algebra and Its Applications",    "MATH2402", 25.00, "Like new",
     "Barely opened — withdrew from unit. Your gain!"),
    (3, "Business Statistics",                    "STAT2401", 20.00, "Acceptable",
     "Spine worn but readable throughout. All problems still legible."),
    (3, "Database System Concepts 7th Ed.",       "CITS3200", 50.00, "New",
     "Bought the wrong edition, never opened. Still in original shrink wrap."),
    (4, "Engineering Mathematics",                "MATH1011", 35.00, "Good",
     "Good condition, a few folded page corners but pages are clean."),
    (5, "Molecular Cell Biology 8th Ed.",         "BIOC2002", 55.00, "Like new",
     "International edition — same content, smaller price. Highly recommend."),
    (6, "Principles of Marketing",                "MKTG1100", 22.00, "Acceptable",
     "Some yellow highlighting throughout. Notes in margins are actually helpful."),
    (7, "Financial Accounting",                   "ACCT1101", 28.00, "Good",
     "Previous owner's name on inside cover. Otherwise clean throughout."),
]

NOTES = [
    # (author_idx, title, unit_code, semester, description, upvotes)
    (0, "CITS3403 Complete Lecture Summary S1",  "CITS3403", "S1 2025",
     "All 12 weeks condensed into 40 pages. Covers Flask, JS, SQL, testing. "
     "Structured by week with key diagrams reproduced in text.",
     47),
    (0, "CITS3403 Final Exam Cheat Sheet",       "CITS3403", "S1 2025",
     "One-page A4 summary allowed in exam. Key patterns and gotchas from past papers. "
     "Covers REST, SQL injection, testing strategies.",
     38),
    (1, "CITS2200 Algorithm Analysis Notes",     "CITS2200", "S1 2025",
     "Big-O, sorting algorithms, graph traversals with worked examples. "
     "Includes Dijkstra, Bellman-Ford, and dynamic programming patterns.",
     29),
    (1, "CITS2002 Systems Programming Guide",    "CITS2002", "S2 2024",
     "C pointers, memory management, process management with diagrams. "
     "File I/O section particularly thorough — covers fork/exec/wait.",
     24),
    (2, "MATH1012 Calculus Week 1–6 Notes",      "MATH1012", "S1 2025",
     "Limits, derivatives, integrals — clear explanations with worked examples. "
     "Integration by parts and substitution covered in detail.",
     19),
    (2, "MATH2402 Linear Algebra Summary",       "MATH2402", "S1 2025",
     "Eigenvalues, vector spaces, matrix decompositions. "
     "All key theorems stated with proofs where they appeared in lectures.",
     15),
    (3, "STAT2401 R Code Cheatsheet",            "STAT2401", "S2 2024",
     "All the R snippets you need for the practicals in one file. "
     "Covers ggplot2, dplyr, lm, and hypothesis testing functions.",
     33),
    (4, "CITS3003 Graphics OpenGL Notes",        "CITS3003", "S1 2025",
     "Week-by-week notes covering shaders, transformations, lighting. "
     "Includes working GLSL fragment and vertex shader examples.",
     11),
    (5, "BIOC2002 Protein Synthesis Summary",    "BIOC2002", "S1 2025",
     "Transcription → translation, with annotated diagrams. "
     "Post-translational modifications and protein folding overview.",
     8),
    (6, "MKTG1100 Marketing Mix Notes",          "MKTG1100", "S2 2024",
     "4Ps framework, case studies, and common exam questions. "
     "Real-world examples from Australian brands used throughout.",
     6),
]

SESSIONS = [
    # (host_idx, title, unit_code, location, days_from_now, max_att, description)
    (0, "CITS3403 Project 2 Sprint Planning",  "CITS3403",
     "Reid Library Level 2, Bay 14",       3,  6,
     "Going through the marking rubric and splitting tasks for the final sprint. "
     "Bring your laptop and your code."),
    (1, "CITS2200 Exam Prep — Algorithms",     "CITS2200",
     "Computer Science Building G.14",     5,  8,
     "Working through past papers together. Bring your notes. "
     "Focus on graph algorithms and dynamic programming."),
    (2, "MATH1012 Calculus Study Group",       "MATH1012",
     "Barry J Marshall Library",           2, 10,
     "Weekly study group, open to anyone struggling with integration. "
     "We go through practice problems and help each other."),
    (3, "CITS2002 Systems Programming Help",   "CITS2002",
     "Reid Library Level 3",               7,  5,
     "Helping with the C assignment — pointers and file I/O. "
     "Small group, come with specific questions."),
    (4, "STAT2401 R Practical Walkthrough",    "STAT2401",
     "Education Building G.21",            1, 12,
     "Running through the week 8 practical before the due date. "
     "Will cover ggplot2 visualisations and regression models."),
    (0, "CITS3403 Flask Backend Q&A",          "CITS3403",
     "Online — Discord link in bio",       4, 20,
     "Open session — ask anything about the Flask backend and SQLite schema. "
     "Recording will be shared in the group chat afterward."),
]

BOUNTIES = [
    # (poster_idx, title, unit_code, reward, description)
    (0, "Need CITS3403 project partner for final sprint", "CITS3403", 0,
     "Looking for one more person to join our group. We have frontend done, need backend help. "
     "Strong Git skills required."),
    (1, "Past exam papers for CITS2200",                 "CITS2200", 10.00,
     "Will pay $10 for any past CITS2200 exam papers from 2022 or earlier. "
     "PDFs or photos both fine."),
    (2, "Tutor needed for MATH1012 — $30/hr",            "MATH1012", 30.00,
     "Struggling with integration techniques. Need 2–3 sessions before the exam. "
     "Can meet on campus or online."),
    (3, "Anyone selling a CITS3002 textbook?",           "CITS3002", 0,
     "Need the Tanenbaum networking book ASAP. Can pick up anywhere on campus. "
     "Happy to pay fair price."),
    (4, "Proofread my ENGL1000 essay — $15",             "ENGL1000", 15.00,
     "1500 word essay on postcolonial literature. Need feedback within 48 hours. "
     "Focus on argument clarity and referencing."),
    (5, "Lost UWA student card — reward for return",     "",         20.00,
     "Lost near Guild Village on Tuesday. Name on card. No questions asked. "
     "Contact me via messages here."),
    (6, "Looking for ACCT1101 study notes",              "ACCT1101", 5.00,
     "Specifically need notes on the double-entry bookkeeping lectures. "
     "Will pay $5 or trade my MKTG1100 notes."),
]

# RSVPs: (session_idx, [user_indices])
RSVPS = [
    (0, [1, 2, 3]),
    (1, [0, 3, 4, 5]),
    (2, [0, 1, 5, 6, 7]),
    (3, [0, 2]),
    (4, [1, 2, 3, 6]),
    (5, [1, 2, 3, 4, 5, 6, 7]),
]

# Saved listings: (user_idx, [listing_indices])
SAVED = [
    (2, [0, 3, 7]),
    (3, [1, 4]),
    (4, [0, 2, 5]),
    (5, [7, 8]),
    (6, [1, 3]),
    (7, [0, 10]),
]

# Ratings: (rater_idx, rated_idx, listing_idx, score, comment)
RATINGS = [
    (2, 0, 0, 5, "Book was exactly as described, super fast reply!"),
    (3, 0, 1, 5, "Jess is a legend, smooth transaction."),
    (4, 1, 2, 4, "Good condition, took a day to reply but all good."),
    (5, 1, 3, 5, "Perfect, met on campus, no issues."),
    (0, 2, 4, 4, "Minor pencil marks but she was upfront about it."),
    (1, 3, 7, 5, "Brand new as advertised!"),
]

# Messages: (sender_idx, receiver_idx, body, minutes_ago)
MESSAGES = [
    # Liam ↔ Jessica — negotiating the CLRS book
    (1, 0, "Hey Jess! Is the CLRS book still available?",                            200),
    (0, 1, "Yes it is! $60 or best offer. Can meet at Reid Library.",                190),
    (1, 0, "Perfect, how about Thursday 2pm?",                                       185),
    (0, 1, "Works for me! See you at the main entrance.",                            180),
    (1, 0, "Awesome, thanks! See you then.",                                         175),

    # Priya → Jessica — asking about the cheat sheet
    (2, 0, "Hi! Is your CITS3403 cheat sheet still accurate for this semester?",     120),
    (0, 2, "Yep, updated it last week. DM me if you want the PDF.",                  115),
    (2, 0, "That would be amazing, thank you so much!",                              110),
    (0, 2, "No worries — I'll upload it to the notes section tonight.",              105),

    # Callum → Liam — study session
    (3, 1, "Hey Liam, could you help me with the CITS2200 graph traversal stuff?",  300),
    (1, 3, "Sure! I'm running a study session Thursday at CS building. Come along.", 295),
    (3, 1, "I RSVP'd already — looking forward to it!",                             290),
    (1, 3, "Great, bring your notes on BFS/DFS.",                                   285),

    # Mei → Priya — calculus textbook
    (4, 2, "Hi Priya, do you still have the Calculus textbook?",                    400),
    (2, 4, "Sold it last week sorry! But I can share my handwritten notes.",        395),
    (4, 2, "Yes please! That would be super helpful for the exam.",                 390),
    (2, 4, "I'll upload them to the notes section tonight.",                        385),
    (4, 2, "You're a lifesaver, thank you!",                                        380),

    # Oliver → Callum — CITS3002 textbook
    (5, 3, "Callum, do you know anyone with a good CITS3002 textbook?",             500),
    (3, 5, "I have one listed on the marketplace — check it out!",                  495),
    (5, 3, "Oh nice, just saved it. Is the condition really acceptable?",           490),
    (3, 5, "Haha it's fine, just a bit of spine wear. Pages are perfect.",          485),
    (5, 3, "Ok cool, I'll message you if I decide to buy.",                         480),

    # Aisha ↔ Tom — ACCT1101 notes
    (6, 7, "Tom, did you find the ACCT1101 notes yet?",                             600),
    (7, 6, "Not yet! Your listing is the only lead I have.",                        595),
    (6, 7, "I might have some old ones from my first year. I'll check tonight.",    590),
    (7, 6, "That would save my life, thank you!",                                   585),
    (6, 7, "Found them! They're not perfect but should help. I'll upload tomorrow.",580),

    # Jessica → Callum — promoting the Flask Q&A
    (0, 3, "Callum, coming to my Flask Q&A session this week?",                     2880),
    (3, 0, "Definitely! Already RSVP'd. Any pre-reading you recommend?",            2870),
    (0, 3, "Just review the SQLAlchemy ORM docs. We'll work through queries live.", 2860),
    (3, 0, "Perfect. See you there!",                                               2855),

    # Oliver → Jessica — general question
    (5, 0, "Hi Jessica! Is the leaderboard updated weekly or in real-time?",        50),
    (0, 5, "Real-time! XP updates the moment you post, RSVP, or sell something.",   45),
    (5, 0, "Nice, that's motivation to actually contribute. Thanks!",               40),
]


# ─────────────────────────────────────────────────────────────────
# Extra content for --full mode
# ─────────────────────────────────────────────────────────────────

EXTRA_USERS = [
    ("Sophie",   "Anderson", "23001009@student.uwa.edu.au",  "password123", 1100, "Hustler",
     "Psych major with a passion for stats and research methods."),
    ("Marcus",   "Lee",      "23001010@student.uwa.edu.au",  "password123",  760, "Hustler",
     "Software engineer in training. Full-stack by day, gamer by night."),
    ("Zara",     "Khan",     "23001011@student.uwa.edu.au",  "password123",  530, "Newbie",
     "Pre-med student balancing lectures, labs, and life."),
    ("Ethan",    "Brown",    "23001012@student.uwa.edu.au",  "password123",  480, "Newbie",
     "Economics and data science. Love finding patterns in messy data."),
    ("Isabella", "Rossi",    "23001013@student.uwa.edu.au",  "password123",  390, "Newbie",
     "Law/Commerce double degree. Interested in corporate and IP law."),
    ("Noah",     "Williams", "23001014@student.uwa.edu.au",  "password123",  310, "Newbie",
     "Environmental science. Passionate about climate data and sustainability."),
    ("Grace",    "Taylor",   "23001015@student.uwa.edu.au",  "password123",  220, "Newbie",
     "Nursing student. High-pressure, high-reward — love it."),
    ("Jayden",   "Scott",    "23001016@student.uwa.edu.au",  "password123",  170, "Newbie",
     "Mechanical engineering first year. Robotics club member."),
    ("Chloe",    "Martin",   "23001017@student.uwa.edu.au",  "password123",  140, "Newbie",
     "Arts student majoring in history and digital humanities."),
    ("Ryan",     "Hall",     "23001018@student.uwa.edu.au",  "password123",  110, "Newbie",
     "Physics undergrad. If it involves maths, I'm probably interested."),
    ("Ella",     "White",    "23001019@student.uwa.edu.au",  "password123",   90, "Newbie",
     "Biochemistry second year. Lab work is my happy place."),
    ("Daniel",   "Harris",   "23001020@student.uwa.edu.au",  "password123",   60, "Newbie",
     "Commerce first year. Still figuring out what to specialise in."),
]

EXTRA_LISTINGS = [
    # (seller_offset from end of USERS+EXTRA_USERS, title, unit_code, price, condition, desc)
    # seller_offset 0 = Sophie (index 8), 1 = Marcus (9), ...
    (0, "Research Methods in Psychology",        "PSYC2207", 32.00, "Good",      "Used for one semester, minor annotations throughout."),
    (0, "Statistics for Behavioural Sciences",   "PSYC1102", 28.00, "Like new",  "Barely used. Great complement to the lecture slides."),
    (1, "Clean Code by Robert Martin",           "CITS3200", 35.00, "Good",      "Essential reading for any software engineer. A few dog-ears."),
    (1, "JavaScript: The Good Parts",            "CITS3403", 18.00, "Acceptable","Old edition but the core concepts are timeless."),
    (2, "Anatomy & Physiology 10th Ed.",         "SCIE1106", 50.00, "Good",      "Some highlighting in the respiratory chapter."),
    (3, "Principles of Economics 7th Ed.",       "ECON1000", 40.00, "Like new",  "Switched to online resources — this is basically new."),
    (4, "Contract Law in Australia",             "LAWS1113", 55.00, "Good",      "Annotations from tutorial prep — actually helpful notes."),
    (5, "Environmental Systems & Societies",     "SCIE2208", 30.00, "Acceptable","Coffee ring on back cover, content pristine."),
    (6, "Fundamentals of Nursing 9th Ed.",       "NURS1001", 65.00, "Like new",  "International edition. Perfect condition."),
    (7, "Engineering Mechanics: Statics",        "MECH1001", 45.00, "Good",      "A few pencil marks, otherwise very clean."),
    (8, "The Penguin History of the World",      "HIST1001", 15.00, "Acceptable","Well-loved but readable. Great for context."),
    (9, "University Physics 14th Ed.",           "PHYS1002", 58.00, "Good",      "Standard introductory physics. Solid condition."),
]

EXTRA_NOTES = [
    (0, "PSYC1102 Stats for Psych Summary",     "PSYC1102", "S1 2025",
     "Covers t-tests, ANOVA, and regression in plain English. Perfect pre-exam review.", 14),
    (1, "CITS3200 Software Engineering Notes",  "CITS3200", "S1 2025",
     "Agile, UML diagrams, testing patterns, and project management frameworks.", 9),
    (2, "SCIE1106 Anatomy Key Terms Glossary",  "SCIE1106", "S1 2025",
     "700+ anatomical terms with definitions and memory aids.", 7),
    (3, "ECON1000 Micro & Macro Crash Course",  "ECON1000", "S2 2024",
     "Supply/demand, elasticity, GDP — all the essentials without the waffle.", 12),
    (4, "LAWS1113 Contract Law Case List",      "LAWS1113", "S1 2025",
     "All key cases with facts, ratio, and exam relevance rating.", 18),
    (5, "SCIE2208 Climate Systems Notes",       "SCIE2208", "S2 2024",
     "Covers carbon cycles, feedback loops, and climate modelling.", 5),
]

EXTRA_SESSIONS = [
    (0, "PSYC1102 Stats Study Circle",          "PSYC1102",
     "Guild Village Café",                      3,  8,
     "Weekly stats help session. SPSS and Excel both welcome."),
    (1, "Web Dev Portfolio Workshop",           "CITS3200",
     "Computer Science Building G.14",          6, 15,
     "Building your portfolio site together. GitHub Pages or Vercel — your choice."),
    (3, "ECON1000 Tutorial Prep",               "ECON1000",
     "Barry J Marshall Library",                2, 10,
     "Going through this week's tutorial questions before class."),
    (4, "LAWS1113 Case Study Discussion",       "LAWS1113",
     "Law Library Meeting Room 3",              4,  6,
     "Analysing landmark contract law cases. Come prepared to discuss."),
]

EXTRA_BOUNTIES = [
    (0, "Need PSYC study group for finals",      "PSYC1102", 0,
     "Looking for 3–4 people to form a study group before finals. DM me."),
    (1, "Buy my old coding laptop — $400",       "",         400.00,
     "Dell XPS 13, 2022, i7, 16GB RAM. Runs Linux perfectly. Campus pickup."),
    (3, "Help setting up Python environment",    "CITS1401", 10.00,
     "Still getting VS Code and conda working on Windows. 1hr help, $10."),
    (5, "Swap SCIE notes for MATH notes",        "SCIE2208", 0,
     "I have detailed SCIE2208 notes. Looking to trade for MATH2402 notes."),
]


# ─────────────────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────────────────

def _now():
    return datetime.now(timezone.utc)


def reset_db():
    """Delete all records from every table (reverse dependency order)."""
    print("Wiping database records...")
    db.session.execute(db.text("DELETE FROM ratings"))
    db.session.execute(db.text("DELETE FROM saved_listings"))
    db.session.execute(db.text("DELETE FROM session_rsvps"))
    db.session.execute(db.text("DELETE FROM messages"))
    db.session.execute(db.text("DELETE FROM post_likes"))
    db.session.execute(db.text("DELETE FROM posts"))
    db.session.execute(db.text("DELETE FROM bounties"))
    db.session.execute(db.text("DELETE FROM sessions"))
    db.session.execute(db.text("DELETE FROM notes"))
    db.session.execute(db.text("DELETE FROM listings"))
    db.session.execute(db.text("DELETE FROM users"))
    db.session.commit()
    print("  ✓ All records removed")


def seed_core():
    """Insert the core 8-user dataset."""
    now = _now()

    # ── Users
    user_objs = []
    for first, last, email, pw, xp, rank, bio in USERS:
        u = User(first_name=first, last_name=last, email=email,
                 xp=xp, rank=rank, bio=bio)
        u.set_password(pw)
        db.session.add(u)
        user_objs.append(u)
    db.session.flush()  # get IDs without committing
    print(f"  ✓ {len(user_objs)} users")

    # ── Listings
    listing_objs = []
    for seller_i, title, unit, price, cond, desc in LISTINGS:
        lst = Listing(seller_id=user_objs[seller_i].id,
                      title=title, unit_code=unit,
                      price=price, condition=cond, description=desc)
        db.session.add(lst)
        listing_objs.append(lst)
    db.session.flush()
    print(f"  ✓ {len(listing_objs)} listings")

    # ── Notes
    for author_i, title, unit, sem, desc, upvotes in NOTES:
        db.session.add(Note(author_id=user_objs[author_i].id,
                            title=title, unit_code=unit,
                            semester=sem, description=desc, upvotes=upvotes))
    db.session.flush()
    print(f"  ✓ {len(NOTES)} notes")

    # ── Study sessions
    session_objs = []
    for host_i, title, unit, location, days, max_att, desc in SESSIONS:
        sess = StudySession(
            host_id=user_objs[host_i].id,
            title=title, unit_code=unit, location=location,
            session_date=now + timedelta(days=days),
            max_attendees=max_att, description=desc,
        )
        db.session.add(sess)
        session_objs.append(sess)
    db.session.flush()
    print(f"  ✓ {len(session_objs)} sessions")

    # ── RSVPs
    rsvp_count = 0
    for sess_i, user_indices in RSVPS:
        for user_i in user_indices:
            db.session.add(SessionRSVP(
                session_id=session_objs[sess_i].id,
                user_id=user_objs[user_i].id,
            ))
            rsvp_count += 1
    db.session.flush()
    print(f"  ✓ {rsvp_count} RSVPs")

    # ── Bounties
    for poster_i, title, unit, reward, desc in BOUNTIES:
        db.session.add(Bounty(poster_id=user_objs[poster_i].id,
                              title=title, unit_code=unit or '',
                              reward=reward, description=desc))
    db.session.flush()
    print(f"  ✓ {len(BOUNTIES)} bounties")

    # ── Saved listings
    saved_count = 0
    for user_i, listing_indices in SAVED:
        for l_i in listing_indices:
            if l_i < len(listing_objs):
                db.session.add(SavedListing(user_id=user_objs[user_i].id,
                                            listing_id=listing_objs[l_i].id))
                saved_count += 1
    db.session.flush()
    print(f"  ✓ {saved_count} saved listings")

    # ── Ratings
    for rater_i, rated_i, listing_i, score, comment in RATINGS:
        db.session.add(Rating(
            rater_id=user_objs[rater_i].id,
            rated_id=user_objs[rated_i].id,
            listing_id=listing_objs[listing_i].id,
            score=score, comment=comment,
        ))
        user_objs[rated_i].rating_sum += score
        user_objs[rated_i].rating_count += 1
    db.session.flush()
    print(f"  ✓ {len(RATINGS)} ratings")

    # ── Messages
    for sender_i, recv_i, body, mins_ago in MESSAGES:
        db.session.add(Message(
            sender_id=user_objs[sender_i].id,
            receiver_id=user_objs[recv_i].id,
            body=body,
            created_at=now - timedelta(minutes=mins_ago),
            read=1,
        ))
    db.session.flush()
    print(f"  ✓ {len(MESSAGES)} messages")

    # ── Posts
    CORE_POSTS = [
        # (user_idx, post_type, body, hours_ago, likes)
        (0, 'general',  "Just finished my CITS3200 project — REST API in Flask, full test suite, deployed. If anyone needs help with Flask or SQLAlchemy hit me up!", 2, 14),
        (1, 'resource', "CLRS 4th edition is absolutely essential if you're doing CITS2200. The pseudocode is much cleaner than the 3rd edition. Worth every cent.", 5, 9),
        (2, 'event',    "Study session for STAT2401 this Thursday at Reid Library Level 3, 4–6pm. We'll be working through Week 9 problem sets. All welcome!", 8, 7),
        (3, 'news',     "UWA CS department just announced new electives for 2026 — Machine Learning Systems and Distributed Computing. Enrolment opens next Monday.", 12, 11),
        (4, 'general',  "Anyone else finding PHIL1001 surprisingly useful for thinking about AI ethics? I keep citing it in my CompSci essays lol", 18, 5),
        (5, 'resource', "Posted my full MATH1722 notes from Semester 1 — all 12 weeks, typed up in LaTeX. Check the Notes section. Free to download.", 24, 18),
        (6, 'event',    "Hackathon at Guild Village this Saturday! Teams of 2–4. Theme is 'Smart Campus'. Prizes up to $500. Sign up at the Guild desk.", 30, 22),
        (7, 'news',     "Reminder: HASS enrolment changes apply from next semester. Double-check your degree plan in StudentConnect before Week 10.", 36, 3),
        (0, 'resource', "My CITS3001 revision notes are up — covers all algorithm complexity proofs we did in tutorials. Should help for the final.", 48, 8),
        (1, 'general',  "Hot take: office hours are criminally underused. Just had a 30-min chat with the CITS2200 unit coordinator and it cleared up 3 weeks of confusion.", 60, 16),
        (2, 'event',    "FREE Python workshop next Tuesday, 1–3pm in CS building Lab 2. Beginners welcome. Just bring your laptop.", 72, 12),
        (3, 'news',     "The Guild is running a textbook buyback scheme this week. Drop off your old books at the Guild building for vouchers.", 96, 6),
    ]
    for u_i, ptype, body, hrs_ago, likes in CORE_POSTS:
        db.session.add(Post(
            author_id=user_objs[u_i].id,
            body=body,
            post_type=ptype,
            created_at=now - timedelta(hours=hrs_ago),
            likes_count=likes,
        ))
    db.session.flush()
    print(f"  ✓ {len(CORE_POSTS)} posts")

    db.session.commit()
    return user_objs, listing_objs, session_objs


def seed_extra(user_objs, listing_objs, session_objs):
    """Add the expanded dataset on top of core seed."""
    now = _now()

    # ── Extra users
    extra_user_objs = []
    for first, last, email, pw, xp, rank, bio in EXTRA_USERS:
        u = User(first_name=first, last_name=last, email=email,
                 xp=xp, rank=rank, bio=bio)
        u.set_password(pw)
        db.session.add(u)
        extra_user_objs.append(u)
    db.session.flush()
    all_extra = extra_user_objs
    print(f"  ✓ {len(all_extra)} extra users")

    # ── Extra listings (sellers are extra users)
    extra_listing_objs = []
    for seller_offset, title, unit, price, cond, desc in EXTRA_LISTINGS:
        if seller_offset < len(all_extra):
            lst = Listing(seller_id=all_extra[seller_offset].id,
                          title=title, unit_code=unit,
                          price=price, condition=cond, description=desc)
            db.session.add(lst)
            extra_listing_objs.append(lst)
    db.session.flush()
    print(f"  ✓ {len(extra_listing_objs)} extra listings")

    # ── Extra notes
    for author_offset, title, unit, sem, desc, upvotes in EXTRA_NOTES:
        if author_offset < len(all_extra):
            db.session.add(Note(author_id=all_extra[author_offset].id,
                                title=title, unit_code=unit,
                                semester=sem, description=desc, upvotes=upvotes))
    db.session.flush()
    print(f"  ✓ {len(EXTRA_NOTES)} extra notes")

    # ── Extra sessions
    for host_offset, title, unit, location, days, max_att, desc in EXTRA_SESSIONS:
        if host_offset < len(all_extra):
            db.session.add(StudySession(
                host_id=all_extra[host_offset].id,
                title=title, unit_code=unit, location=location,
                session_date=now + timedelta(days=days),
                max_attendees=max_att, description=desc,
            ))
    db.session.flush()
    print(f"  ✓ {len(EXTRA_SESSIONS)} extra sessions")

    # ── Extra bounties
    for poster_offset, title, unit, reward, desc in EXTRA_BOUNTIES:
        if poster_offset < len(all_extra):
            db.session.add(Bounty(poster_id=all_extra[poster_offset].id,
                                  title=title, unit_code=unit or '',
                                  reward=reward, description=desc))
    db.session.flush()
    print(f"  ✓ {len(EXTRA_BOUNTIES)} extra bounties")

    # ── Cross-saves: extra users save some core listings
    cross_saves = [
        (0, 0), (0, 5), (1, 1), (1, 7), (2, 2),
        (3, 4), (4, 6), (5, 8), (6, 9), (7, 0),
    ]
    save_count = 0
    for eu_i, l_i in cross_saves:
        if eu_i < len(all_extra) and l_i < len(listing_objs):
            db.session.add(SavedListing(user_id=all_extra[eu_i].id,
                                        listing_id=listing_objs[l_i].id))
            save_count += 1
    db.session.flush()
    print(f"  ✓ {save_count} extra saved listings")

    # ── Extra messages between extra users and core users
    extra_messages = [
        (all_extra[0].id, user_objs[0].id, "Hi Jessica! Any tips for balancing study and campus life?", 72 * 60),
        (user_objs[0].id, all_extra[0].id, "Honestly? Use UniShare. Post your notes, join sessions, earn XP. It helps!", 71 * 60 + 50),
        (all_extra[0].id, user_objs[0].id, "Already on it. Love the platform!", 71 * 60 + 40),

        (all_extra[1].id, user_objs[1].id, "Marcus here, loved your algorithm notes. Any chance of a CITS3200 version?", 96 * 60),
        (user_objs[1].id, all_extra[1].id, "Working on it! Should be up by end of semester.", 95 * 60 + 55),

        (all_extra[2].id, user_objs[2].id, "Priya, your MATH notes saved my last assignment. Thank you!", 36 * 60),
        (user_objs[2].id, all_extra[2].id, "So glad they helped! Good luck with the exam.", 35 * 60 + 50),

        (all_extra[3].id, user_objs[3].id, "Callum, what IDE do you use for C programming?", 120 * 60),
        (user_objs[3].id, all_extra[3].id, "VS Code with clangd. Absolute game changer. DM me the config.", 119 * 60 + 45),
        (all_extra[3].id, user_objs[3].id, "That's exactly what I needed. Coming to your session for sure!", 119 * 60 + 30),
    ]
    for sender_id, recv_id, body, mins_ago in extra_messages:
        db.session.add(Message(
            sender_id=sender_id, receiver_id=recv_id,
            body=body,
            created_at=now - timedelta(minutes=mins_ago),
            read=1,
        ))
    db.session.flush()
    print(f"  ✓ {len(extra_messages)} extra messages")

    # ── Extra posts
    all_users = user_objs + extra_user_objs
    extra_posts = [
        # (user_obj, post_type, body, hours_ago, likes)
        (all_users[8],  'resource', "Posted CITS1401 Week 1–6 Python notes — beginner-friendly, lots of worked examples. Perfect if you're just starting out.", 15, 7),
        (all_users[9],  'event',    "ECON1101 group study at Hackett Hall tomorrow, 10am. Covering market structures and game theory. Bring practice papers!", 20, 5),
        (all_users[10], 'general',  "Just got my first internship offer! If anyone wants tips on technical interviews for Perth-based companies, I'm happy to chat.", 28, 31),
        (all_users[11], 'news',     "Library hours extended until midnight during SWOTVAC. All floors open, including group study rooms — book early via the portal.", 40, 9),
    ]
    for u_obj, ptype, body, hrs_ago, likes in extra_posts:
        db.session.add(Post(
            author_id=u_obj.id,
            body=body,
            post_type=ptype,
            created_at=now - timedelta(hours=hrs_ago),
            likes_count=likes,
        ))
    db.session.flush()
    print(f"  ✓ {len(extra_posts)} extra posts")

    db.session.commit()


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    full_mode  = '--full'  in sys.argv
    reset_mode = '--reset' in sys.argv or full_mode

    app = create_app()
    with app.app_context():
        if reset_mode:
            reset_db()

        # Skip if data already exists and not resetting
        existing = User.query.first()
        if existing and not reset_mode:
            print("Database already has data. Use --reset to wipe and re-seed.")
            sys.exit(0)

        print("Seeding database...")
        user_objs, listing_objs, session_objs = seed_core()

        if full_mode:
            print("Seeding extra content (--full mode)...")
            seed_extra(user_objs, listing_objs, session_objs)

        print("\nDone! Log in with any of these accounts (password: password123):")
        print("  jessica  →  23001001@student.uwa.edu.au  (Campus Legend, 2450 XP)")
        print("  liam     →  23001002@student.uwa.edu.au  (Campus Legend, 1820 XP)")
        print("  priya    →  23001003@student.uwa.edu.au  (Hustler, 870 XP)")
        print("  tom      →  23001008@student.uwa.edu.au  (Newbie, 80 XP)")
        if full_mode:
            print("  sophie   →  23001009@student.uwa.edu.au  (Hustler, 1100 XP)")
            print("  marcus   →  23001010@student.uwa.edu.au  (Hustler, 760 XP)")
