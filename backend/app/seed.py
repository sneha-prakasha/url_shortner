"""Fill the database with demo data so the dashboard has something to show.

    python -m app.seed

Login afterwards with  demo@snip.dev / demo12345
"""
import random
from datetime import timedelta

from .database import SessionLocal, init_db
from .models import Click, Link, User, utcnow
from .security import hash_password
from .utils import code_for_id

DEMO_LINKS = [
    ("linkedin", "https://www.linkedin.com/in/your-profile", "LinkedIn", 280),
    ("portfolio", "https://github.com/your-username", "GitHub", 190),
    ("resume", "https://example.com/my-resume.pdf", "Resume", 120),
    (None, "https://www.youtube.com/@your-channel", "YouTube", 75),
    (None, "https://example.com/handmade-shop", "Handmade shop", 40),
]
REFERRERS = ["google.com", "github.com", "t.co", "linkedin.com", "reddit.com", None, None]
DEVICES = ["desktop", "desktop", "mobile", "mobile", "mobile", "tablet"]
BROWSERS = ["Chrome", "Chrome", "Safari", "Firefox", "Edge"]


def main():
    init_db()
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "demo@snip.dev").first():
            print("Demo data already exists.")
            return
        user = User(email="demo@snip.dev", password_hash=hash_password("demo12345"))
        db.add(user)
        db.flush()

        now = utcnow()
        for alias, url, label, clicks in DEMO_LINKS:
            link = Link(user_id=user.id, code=f"tmp{random.randrange(10**9)}",
                        long_url=url, label=label, is_custom=bool(alias),
                        created_at=now - timedelta(days=30))
            db.add(link)
            db.flush()
            link.code = alias or code_for_id(link.id)
            for _ in range(clicks):
                when = now - timedelta(days=random.random() * 30, seconds=random.randrange(86400))
                db.add(Click(
                    link_id=link.id, clicked_at=min(when, now),
                    device=random.choice(DEVICES), browser=random.choice(BROWSERS),
                    referrer_host=random.choice(REFERRERS),
                    source="qr" if random.random() < 0.25 else "link",
                ))
        db.commit()
        print("Seeded. Login: demo@snip.dev / demo12345")
    finally:
        db.close()


if __name__ == "__main__":
    main()
