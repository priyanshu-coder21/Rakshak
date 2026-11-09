from fastapi import APIRouter, HTTPException, Request
from psycopg2.extras import Json

from database.database import get_db_connection

from utils.id_generator import distress_token_id_generator
from utils.ai_extractor import extract_disaster_metrics


router = APIRouter()


@router.post("/api/telegram")
async def telegram_webhook(request: Request):

    telegram_payload = await request.json()

    message = telegram_payload.get("message", {})

    raw_text = message.get("text")

    chat_id = message.get("chat", {}).get("id")

    if not raw_text:
        return {"status": "ignored"}

    latitude = 30.3165
    longitude = 78.0322

    token_id = distress_token_id_generator()

    extracted_data = extract_disaster_metrics(raw_text)

    severity = int(extracted_data.get("severity") or 3)
    vulnerability = int(extracted_data.get("vulnerability") or 3)

    conn = None

    try:
        conn = get_db_connection()

        insert_sql = """
            INSERT INTO DistressTickets (
                token_id,
                raw_message,
                extracted_json,
                location,
                severity,
                vulnerability,
                status
            )
            VALUES (
                %s,
                %s,
                %s,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                %s,
                %s,
                'Pending'
            )
        """

        with conn.cursor() as cur:
            cur.execute(
                insert_sql,
                (
                    token_id,
                    raw_text,
                    Json(extracted_data),
                    longitude,
                    latitude,
                    severity,
                    vulnerability
                )
            )

        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Database insertion failed: {str(e)}"
        ) from e

    finally:
        if conn:
            conn.close()

    return {
        "status": "ok",
        "token_id": token_id
    }