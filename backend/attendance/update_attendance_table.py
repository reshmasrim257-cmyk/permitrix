
from app.database import get_connection


def update_attendance_table():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE attendance_records
                ADD COLUMN IF NOT EXISTS import_id BIGINT
                REFERENCES attendance_imports(id);
            """)

    print("Attendance table updated with import_id!")


if __name__ == "__main__":
    update_attendance_table()
