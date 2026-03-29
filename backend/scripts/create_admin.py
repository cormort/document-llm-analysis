"""建立初始管理員帳號。"""

from sqlalchemy import select

from backend.app.core.database import SessionLocal, init_db
from backend.app.core.security import get_password_hash
from backend.app.models.user import User


def create_admin():
    """建立初始管理員帳號。"""
    init_db()
    db = SessionLocal()

    try:
        existing_admin = db.execute(
            select(User).where(User.username == "admin")
        ).scalar_one_or_none()

        if existing_admin:
            print("管理員帳號已存在")
            print(f"用戶名: admin")
            print("如需重設密碼，請手動修改資料庫")
            return

        admin_user = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123456"),
            is_active=True,
            is_admin=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print("=" * 50)
        print("初始管理員帳號已建立")
        print("=" * 50)
        print(f"用戶名: admin")
        print(f"密碼: admin123456")
        print(f"Email: admin@example.com")
        print("=" * 50)
        print("請登入後立即修改密碼！")
        print("=" * 50)

    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
