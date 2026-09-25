from database import Base, engine
import models
from sqlalchemy import text
from seed_exercises import seed_exercises


def init_db():
    """Idempotently initializes all SQLAlchemy models and seeds required default data."""
    Base.metadata.create_all(bind=engine)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE iot_devices ADD COLUMN IF NOT EXISTS gym_id INTEGER DEFAULT 1;"))
            conn.commit()
    except Exception as e:
        print(f"[DB INIT] Migration check warning: {e}")
    try:
        seed_exercises()
    except Exception as e:
        print(f"[DB INIT] Seed exercises warning: {e}")


if __name__ == "__main__":
    init_db()
    print("Database tables created successfully!")