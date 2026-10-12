
from app.database import get_connection


def create_tables():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_records (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    roll_number VARCHAR(30) NOT NULL,
                    classes_attended INTEGER NOT NULL
                        CHECK (classes_attended >= 0),
                    classes_conducted INTEGER NOT NULL
                        CHECK (classes_conducted >= 0),
                    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CHECK (classes_attended <= classes_conducted)
                );
            """)

    print("attendance_records table created successfully!")


if __name__ == "__main__":
    create_tables()
