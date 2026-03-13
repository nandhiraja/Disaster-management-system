from backend.database import init_db
import os

if __name__ == "__main__":
    if os.path.exists("disaster.db"):
        os.remove("disaster.db")
    init_db()
    print("Database re-initialized with professional schema.")
