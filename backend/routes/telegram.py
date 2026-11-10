from fastapi import APIRouter, HTTPException, Request
from psycopg2.extras import Json

from database.database import get_db_connection

from utils.id_generator import distress_token_id_generator
from utils.ai_extractor import extract_disaster_metrics


router = APIRouter()

from fastapi import APIRouter, HTTPException, Request
from psycopg2.extras import Json
import asyncio
from database.database import get_db_connection
from utils.id_generator import distress_token_id_generator
from utils.ai_extractor import extract_disaster_metrics

router = APIRouter()

# 1. Create an in-memory queue to buffer Telegram messages if Supabase drops
offline_telegram_queue = []

async def flush_telegram_queue():
    """Background task to push buffered messages to Supabase when connection returns."""
    global offline_telegram_queue
    if not offline_telegram_queue:
        return
        
    remaining_queue = []
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            insert_sql = """
                INSERT INTO DistressTickets (
                    token_id, raw_message, extracted_json, location, severity, vulnerability, status
                ) VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, 'Pending')
            """
            for ticket in offline_telegram_queue:
                try:
                    cur.execute(insert_sql, (
                        ticket["token_id"], ticket["raw_text"], Json(ticket["extracted_data"]), 
                        ticket["longitude"], ticket["latitude"], ticket["severity"], ticket["vulnerability"]
                    ))
                except Exception as row_err:
                    print(f"Failed to flush specific buffered ticket: {row_err}")
                    remaining_queue.append(ticket) # Keep if specific row fails
            conn.commit()
            print(f"Successfully flushed {len(offline_telegram_queue) - len(remaining_queue)} buffered Telegram messages.")
    except Exception as db_err:
        print(f"Database still unreachable during flush attempt: {db_err}")
        remaining_queue = offline_telegram_queue # Keep everything if connection fails
    finally:
        if conn:
            conn.close()
        offline_telegram_queue = remaining_queue


@router.post("/api/telegram")
async def telegram_webhook(request: Request):
    telegram_payload = await request.json()
    message = telegram_payload.get("message", {})
    raw_text = message.get("text")

    if not raw_text:
        return {"status": "ignored"}

    latitude = 30.3165
    longitude = 78.0322
    token_id = distress_token_id_generator()
    extracted_data = extract_disaster_metrics(raw_text)

    severity = int(extracted_data.get("severity") or 3)
    vulnerability = int(extracted_data.get("vulnerability") or 3)

    # Prepare the payload for either immediate insert or buffering
    ticket_payload = {
        "token_id": token_id,
        "raw_text": raw_text,
        "extracted_data": extracted_data,
        "longitude": longitude,
        "latitude": latitude,
        "severity": severity,
        "vulnerability": vulnerability
    }

    conn = None
    try:
        # First attempt: Try to insert immediately
        conn = get_db_connection()
        with conn.cursor() as cur:
            insert_sql = """
                INSERT INTO DistressTickets (
                    token_id,
                    raw_message,
                    extracted_json,
                    location,
                    severity,
                    vulnerability,
                    status
                ) VALUES (
                        %s,
                        %s, 
                        %s, 
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        %s,
                        %s, 
                        'Pending')
            """
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
        
        # If successful, try to flush any previously buffered messages in the background
        asyncio.create_task(flush_telegram_queue())

    except Exception as e:
        # LOW CONNECTIVITY FALLBACK: If Supabase connection drops, buffer it locally
        if conn:
            conn.rollback()
        
        print(f"Supabase connection dropped! Buffering Telegram message {token_id} locally.")
        offline_telegram_queue.append(ticket_payload)
        
        # We STILL return HTTP 200 OK to Telegram so it doesn't think our bot is broken
        return {"status": "buffered", "token_id": token_id, "message": "Queued due to low connectivity"}

    finally:
        if conn:
            conn.close()

    return {"status": "ok", "token_id": token_id}