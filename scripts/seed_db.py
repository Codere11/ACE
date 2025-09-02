from datetime import date
from app.services.bootstrap_db import create_all
from app.services.db import SessionLocal
from app.models import User, Tenant, ConversationFlow
from app.services.security import hash_password

def run():
    # create tables
    create_all()

    with SessionLocal() as db:
        # If any users exist, assume already seeded
        if db.query(User).first():
            print("DB already seeded; skipping.")
            return

        # Admin (no tenant)
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            role="admin",
            tenant_id=None,
        )
        db.add(admin)

        # Demo tenant
        t = Tenant(
            slug="demo-agency",
            display_name="Demo Agency",
            last_paid=date.today(),
            contact_name="Demo Person",
            contact_email="demo@example.com",
            contact_phone="+386 40 000 000",
        )
        db.add(t)
        db.flush()  # get t.id

        # Demo manager user
        demo_user = User(
            username="demo",
            password_hash=hash_password("demo123"),
            role="manager",
            tenant_id=t.id,
        )
        db.add(demo_user)

        # Default flow row (kept simple)
        db.add(ConversationFlow(tenant_id=t.id, flow={
            "greetings": ["Živjo! Kako vam lahko pomagam danes?"],
            "intents": [],
            "responses": {}
        }))

        db.commit()
        print("Seeded: admin/admin123 and demo(tenant=demo-agency)/demo123")

if __name__ == "__main__":
    run()
