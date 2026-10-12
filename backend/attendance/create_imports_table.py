
from app.database import get_connection


def create_imports_table():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_imports (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    total_rows INTEGER NOT NULL DEFAULT 0,
                    valid_rows INTEGER NOT NULL DEFAULT 0,
                    invalid_rows INTEGER NOT NULL DEFAULT 0,
                    status VARCHAR(20) NOT NULL DEFAULT 'confirmed'
                        CHECK (status IN ('confirmed', 'failed')),
                    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

    print("attendance_imports table created successfully!")


if __name__ == "__main__":
    create_imports_table()
