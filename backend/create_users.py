from getpass import getpass

from app.database import Base, SessionLocal, engine
from app.models import User
from app.security import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    for role in ("admin", "member"):
        username = input(f"Enter {role} username: ").strip()

        if not username:
            print("Username cannot be empty. Run the script again.")
            break

        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"User '{username}' already exists; leaving it unchanged.")
            continue

        password = getpass(f"Enter password for {username}: ")
        confirmation = getpass("Confirm password: ")

        if len(password) < 12:
            print("Password must be at least 12 characters.")
            break

        if password != confirmation:
            print("Passwords do not match.")
            break

        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            active=True,
        )
        db.add(user)
        db.commit()
        print(f"Created {role} account '{username}'.")

finally:
    db.close()
