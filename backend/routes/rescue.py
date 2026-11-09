from fastapi import APIRouter, HTTPException

from database.database import get_db_connection

from schemas.rescue import (
    RescueRequest,
    RescueResponse
)

from utils.id_generator import rescue_team_id_generator


router = APIRouter()


@router.post(
    "/api/rescue",
    response_model=RescueResponse,
    status_code=201
)
def post_rescue(rescue_data: RescueRequest):

    team_id = rescue_team_id_generator()

    conn = None

    try:
        conn = get_db_connection()

        query = """
            INSERT INTO RescueTeams (
                team_id,
                current_location,
                team_capacity
            )
            VALUES (
                %s,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                %s
            )
        """

        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    team_id,
                    rescue_data.longitude,
                    rescue_data.latitude,
                    rescue_data.team_capacity
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

    return RescueResponse(
        team_id=team_id,
        status="Available",
        message="The rescue team has been registered."
    )


@router.get("/getRescue")
def get_rescue():

    conn = None

    try:
        conn = get_db_connection()

        query = """
            SELECT *
            FROM RescueTeams
        """

        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

            result = []

            for row in rows:
                result.append({
                    "team_id": row[0],
                    "location": row[1],
                    "status": row[2],
                    "capacity": row[3]
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