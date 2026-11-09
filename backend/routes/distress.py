from fastapi import APIRouter, HTTPException
from psycopg2.extras import Json

from database.database import get_db_connection

from schemas.distress import (
    DistressRequest,
    DistressResponse
)

from utils.id_generator import distress_token_id_generator
from utils.ai_extractor import extract_disaster_metrics

router = APIRouter()


@router.post(
    "/api/reportDistress",
    response_model=DistressResponse,
    status_code=201
)
def report_distress(distress_data: DistressRequest):

    token_id = distress_token_id_generator()

    extracted_data = extract_disaster_metrics(
        distress_data.raw_message
    )

    severity = int(extracted_data.get("severity") or 3)
    vulnerability = int(extracted_data.get("vulnerability") or 3)

    insert_sql_query = """
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

    conn = None

    try:
        conn = get_db_connection()

        with conn.cursor() as cur:
            cur.execute(
                insert_sql_query,
                (
                    token_id,
                    distress_data.raw_message,
                    Json(extracted_data),
                    distress_data.longitude,
                    distress_data.latitude,
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
            detail=f"Database Error: {str(e)}"
        ) from e

    finally:
        if conn:
            conn.close()

    return DistressResponse(
        token_id=token_id,
        status="Pending",
        extracted_data=extracted_data,
        message="Distress report registered successfully. Keep your tracking token safe."
    )


@router.get("/api/getDistress")
def get_distress():

    conn = None

    try:
        conn = get_db_connection()

        query = """
            SELECT *
            FROM DistressTickets
        """

        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

            result = []

            for row in rows:
                result.append({
                    "token_id": row[0],
                    "raw_message": row[1],
                    "extracted_json": row[2],
                    "location": row[3],
                    "severity": row[4],
                    "vulnerability": row[5],
                    "wait_time_start": row[6],
                    "vwps_score": row[7],
                    "status": row[8]
                })

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        ) from e

    finally:
        if conn:
            conn.close()