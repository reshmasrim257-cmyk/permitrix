from app.database import get_connection

try:
    connection = get_connection()
    print("PostgreSQL connection successful!")

    connection.close()
    print("Database connection closed.")

except Exception as error:
    print("Database connection failed.")
    print("Error:", error)