import csv
import io

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.database import get_connection


app = FastAPI(
    title="EventFlow Attendance API",
    description="Attendance import and eligibility module",
    version="1.0.0",
)


class EligibilitySettingUpdate(BaseModel):
    minimum_percentage: float = Field(ge=0, le=100)


def parse_attendance_csv(content: bytes):
    try:
        text_content = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="The CSV must use UTF-8 text encoding.",
        )

    reader = csv.DictReader(io.StringIO(text_content))

    required_columns = {
        "roll_number",
        "classes_attended",
        "classes_conducted",
    }

    if not reader.fieldnames:
        raise HTTPException(
            status_code=400,
            detail="CSV header is missing.",
        )

    reader.fieldnames = [
        name.strip() if name else "" for name in reader.fieldnames
    ]

    if not required_columns.issubset(set(reader.fieldnames)):
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Required CSV columns are missing.",
                "required_columns": sorted(required_columns),
                "received_columns": reader.fieldnames,
            },
        )

    records = []
    errors = []

    for row_number, row in enumerate(reader, start=2):
        try:
            roll_number = (row.get("roll_number") or "").strip()

            if not roll_number:
                raise ValueError("Roll number is missing.")

            attended = int(row["classes_attended"])
            conducted = int(row["classes_conducted"])

            if attended < 0 or conducted < 0:
                raise ValueError("Class counts cannot be negative.")

            if conducted == 0 and attended != 0:
                raise ValueError(
                    "Attended classes must be zero when no classes were conducted."
                )

            if attended > conducted:
                raise ValueError(
                    "Attended classes cannot exceed classes conducted."
                )

            records.append({
                "roll_number": roll_number,
                "classes_attended": attended,
                "classes_conducted": conducted,
                "attendance_percentage": (
                    round(attended / conducted * 100, 2)
                    if conducted > 0
                    else None
                ),
            })

        except (ValueError, TypeError, KeyError) as error:
            errors.append({
                "row": row_number,
                "error": str(error),
            })

    roll_numbers = [record["roll_number"] for record in records]

    if len(roll_numbers) != len(set(roll_numbers)):
        errors.append({
            "row": None,
            "error": "Duplicate roll numbers are not allowed in one import.",
        })

    return records, errors


@app.get("/")
def home():
    return {"message": "EventFlow attendance backend is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/attendance/import/preview")
async def preview_attendance(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )
    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        records, errors = parse_attendance_csv(content)

        return {
            "filename": file.filename,
            "total_rows": len(records) + sum(
                1 for error in errors if error["row"] is not None
            ),
            "valid_rows": len(records),
            "invalid_rows": sum(
                1 for error in errors if error["row"] is not None
            ),
            "records_preview": records,
            "errors": errors,
            "saved_to_database": False,
        }

    finally:
        await file.close()


@app.post("/api/attendance/import/confirm")
async def confirm_attendance_import(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        records, errors = parse_attendance_csv(content)

        if errors:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Import rejected. Fix the CSV errors and try again.",
                    "errors": errors,
                },
            )

        if not records:
            raise HTTPException(
                status_code=400,
                detail="The CSV contains no attendance records.",
            )

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO attendance_imports
                        (filename, total_rows, valid_rows, invalid_rows, status)
                    VALUES (%s, %s, %s, 0, 'confirmed')
                    RETURNING id;
                    """,
                    (file.filename, len(records), len(records)),
                )

                import_id = cursor.fetchone()["id"]

                cursor.executemany(
                    """
                    INSERT INTO attendance_records
                        (
                            roll_number,
                            classes_attended,
                            classes_conducted,
                            import_id
                        )
                    VALUES (%s, %s, %s, %s);
                    """,
                    [
                        (
                            record["roll_number"],
                            record["classes_attended"],
                            record["classes_conducted"],
                            import_id,
                        )
                        for record in records
                    ],
                )

        return {
            "message": "Attendance import saved successfully.",
            "import_id": import_id,
            "filename": file.filename,
            "saved_records": len(records),
            "saved_to_database": True,
        }

    finally:
        await file.close()


@app.get("/api/attendance/import/history")
def get_attendance_import_history():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    filename,
                    total_rows,
                    valid_rows,
                    invalid_rows,
                    status,
                    imported_at
                FROM attendance_imports
                ORDER BY imported_at DESC;
                """
            )

            imports = cursor.fetchall()

    return {
        "total_imports": len(imports),
        "imports": imports,
    }


@app.get("/api/attendance/eligibility/{roll_number}")
def check_attendance_eligibility(roll_number: str):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT minimum_percentage
                FROM eligibility_settings
                ORDER BY id DESC
                LIMIT 1;
                """
            )
            setting = cursor.fetchone()

            if setting is None:
                raise HTTPException(
                    status_code=500,
                    detail="Attendance eligibility threshold is not configured.",
                )

            minimum_percentage = float(setting["minimum_percentage"])

            cursor.execute(
                """
                SELECT
                    roll_number,
                    classes_attended,
                    classes_conducted,
                    imported_at
                FROM attendance_records
                WHERE roll_number = %s
                ORDER BY imported_at DESC, id DESC
                LIMIT 1;
                """,
                (roll_number,),
            )
            student = cursor.fetchone()

    if student is None:
        raise HTTPException(
            status_code=404,
            detail=f"No attendance record found for roll number {roll_number}.",
        )

    attended = student["classes_attended"]
    conducted = student["classes_conducted"]

    percentage = (
        round(attended / conducted * 100, 2)
        if conducted > 0
        else None
    )

    eligible = (
        percentage is not None
        and percentage >= minimum_percentage
    )

    return {
        "roll_number": student["roll_number"],
        "classes_attended": attended,
        "classes_conducted": conducted,
        "attendance_percentage": percentage,
        "minimum_required_percentage": minimum_percentage,
        "eligible": eligible,
        "last_updated": student["imported_at"],
    }


@app.get("/api/attendance/eligibility")
def get_all_attendance_eligibility():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT minimum_percentage
                FROM eligibility_settings
                ORDER BY id DESC
                LIMIT 1;
                """
            )
            setting = cursor.fetchone()

            if setting is None:
                raise HTTPException(
                    status_code=500,
                    detail="Attendance eligibility threshold is not configured.",
                )

            minimum_percentage = float(setting["minimum_percentage"])

            cursor.execute(
                """
                SELECT DISTINCT ON (roll_number)
                    roll_number,
                    classes_attended,
                    classes_conducted,
                    imported_at
                FROM attendance_records
                ORDER BY roll_number, imported_at DESC, id DESC;
                """
            )
            students = cursor.fetchall()

    results = []

    for student in students:
        attended = student["classes_attended"]
        conducted = student["classes_conducted"]

        percentage = (
            round(attended / conducted * 100, 2)
            if conducted > 0
            else None
        )

        eligible = (
            percentage is not None
            and percentage >= minimum_percentage
        )

        results.append({
            "roll_number": student["roll_number"],
            "classes_attended": attended,
            "classes_conducted": conducted,
            "attendance_percentage": percentage,
            "minimum_required_percentage": minimum_percentage,
            "eligible": eligible,
            "last_updated": student["imported_at"],
        })

    return {
        "total_students": len(results),
        "eligible_students": sum(
            1 for student in results if student["eligible"]
        ),
        "ineligible_students": sum(
            1 for student in results if not student["eligible"]
        ),
        "minimum_required_percentage": minimum_percentage,
        "students": results,
    }


@app.put("/api/attendance/eligibility/settings")
def update_eligibility_settings(
    settings: EligibilitySettingUpdate,
):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM eligibility_settings
                ORDER BY id DESC
                LIMIT 1;
                """
            )
            existing_setting = cursor.fetchone()

            if existing_setting is None:
                cursor.execute(
                    """
                    INSERT INTO eligibility_settings (minimum_percentage)
                    VALUES (%s)
                    RETURNING minimum_percentage;
                    """,
                    (settings.minimum_percentage,),
                )
            else:
                cursor.execute(
                    """
                    UPDATE eligibility_settings
                    SET minimum_percentage = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING minimum_percentage;
                    """,
                    (
                        settings.minimum_percentage,
                        existing_setting["id"],
                    ),
                )

            updated_setting = cursor.fetchone()

    return {
        "message": "Eligibility threshold updated successfully.",
        "minimum_required_percentage": float(
            updated_setting["minimum_percentage"]
        ),
    }