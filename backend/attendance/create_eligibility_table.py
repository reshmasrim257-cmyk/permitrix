
from app.database import get_connection


def create_eligibility_table():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS eligibility_settings (
                    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    minimum_percentage NUMERIC(5, 2) NOT NULL
                        CHECK (
                            minimum_percentage >= 0
                            AND minimum_percentage <= 100
                        ),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            cursor.execute("""
                INSERT INTO eligibility_settings (minimum_percentage)
                SELECT 75.00
                WHERE NOT EXISTS (
                    SELECT 1 FROM eligibility_settings
                );
            """)

    print("Eligibility settings table created successfully!")


if __name__ == "__main__":
    create_eligibility_table()
