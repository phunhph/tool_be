from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.db import engine, Base, get_db
from app.models import User, Role

# ---------------- Password Hash ----------------
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# ---------------- Seed Roles ----------------
def seed_roles(db: Session):
    roles = [
        {"name": "master", "description": "Full quyền, không ai sửa được quyền"},
        {"name": "admin", "description": "Có thể xem, tạo, sửa, xóa trừ thay đổi quyền và xoá user"},
        {"name": "viewer", "description": "Chỉ có thể xem"},
    ]
    for r in roles:
        role = db.query(Role).filter(Role.name == r["name"]).first()
        if not role:
            role = Role(name=r["name"], description=r["description"])
            db.add(role)
    db.commit()
    print("Seed roles completed!")

# ---------------- Seed Users ----------------
def seed_users(db: Session):
    # Master
    master_role = db.query(Role).filter(Role.name == "master").first()
    if not db.query(User).filter(User.login_id == "master").first():
        user = User(
            first_name="Master",
            last_name="User",
            login_id="master",
            email="master@example.com",
            password=pwd_context.hash("Master123!"),
            role_id=master_role.id,
            is_delete=False
        )
        db.add(user)

    # Admin
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not db.query(User).filter(User.login_id == "admin").first():
        user = User(
            first_name="Admin",
            last_name="User",
            login_id="admin",
            email="admin@example.com",
            password=pwd_context.hash("Admin123!"),
            role_id=admin_role.id,
            is_delete=False
        )
        db.add(user)

    # Viewer
    viewer_role = db.query(Role).filter(Role.name == "viewer").first()
    if not db.query(User).filter(User.login_id == "viewer").first():
        user = User(
            first_name="Viewer",
            last_name="User",
            login_id="viewer",
            email="viewer@example.com",
            password=pwd_context.hash("Viewer123!"),
            role_id=viewer_role.id,
            is_delete=False
        )
        db.add(user)

    db.commit()
    print("Seed users completed!")

# ---------------- Run ----------------
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    seed_roles(db)
    seed_users(db)
