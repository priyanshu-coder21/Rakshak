from fastapi import APIRouter, HTTPException

from database.database import get_db_connection

from schemas.dispatch import RescueCompleteRequest


router = APIRouter()


@router.post("/api/dispatch/run")
def run_dispatch():

    conn = None

    try:
        conn = get_db_connection()

        with conn.cursor() as cursor:

            match_query = """
                WITH HighestPriorityVictim AS (
                    SELECT token_id, location
                    FROM DistressTickets
                    WHERE status = 'Pending'
                    ORDER BY vwps_score DESC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                ),
                NearestTeam AS (
                    SELECT team_id
                    FROM RescueTeams, HighestPriorityVictim
                    WHERE RescueTeams.status = 'Available'
                    ORDER BY ST_Distance(
                        RescueTeams.current_location,
                        HighestPriorityVictim.location
                    ) ASC
                    LIMIT 1
                    FOR UPDATE OF RescueTeams SKIP LOCKED
                )
                SELECT
                    (SELECT token_id FROM HighestPriorityVictim),
                    (SELECT team_id FROM NearestTeam)
            """

            cursor.execute(match_query)
            match = cursor.fetchone()

            if not match or not match[0] or not match[1]:
                raise HTTPException(
                    status_code=404,
                    detail="No pending victims or available teams found."
                )

            victim_token, team_id = match

            cursor.execute(
                """
                INSERT INTO Dispatch_Logs (
                    token_id,
                    team_id,
                    rescue_status
                )
                VALUES (%s, %s, 'In Process')
                """,
                (victim_token, team_id)
            )

            cursor.execute(
                """
                UPDATE DistressTickets
                SET status = 'Dispatched'
                WHERE token_id = %s
                """,
                (victim_token,)
            )

            cursor.execute(
                """
                UPDATE RescueTeams
                SET status = 'In_Transit'
                WHERE team_id = %s
                """,
                (team_id,)
            )

        conn.commit()

        return {
            "status": "Success",
            "assigned_victim": victim_token,
            "assigned_team": team_id
        }

    except HTTPException:
        if conn:
            conn.rollback()
        raise

    except Exception as e:
        if conn:
            conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Dispatch error: {str(e)}"
        ) from e

    finally:
        if conn:
            conn.close()


@router.get("/getDispatchLogs")
def get_dispatch_logs():

    conn = None

    try:
        conn = get_db_connection()

        query = """
            SELECT *
            FROM Dispatch_Logs
        """

        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

            result = []

            for row in rows:
                result.append({
                    "log_id": row[0],
                    "token_id": row[1],
                    "team_id": row[2],
                    "dispatch_time": row[3],
                    "rescue_status": row[4],
                    "sns_alert_sent": row[5]
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


@router.post("/api/dispatch/complete")
def complete_rescue(payload: RescueCompleteRequest):

    conn = None

    try:
        conn = get_db_connection()

        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE Dispatch_Logs
                SET rescue_status = 'Completed'
                WHERE token_id = %s
                  AND team_id = %s
                  AND rescue_status = 'In Process'
                """,
                (payload.token_id, payload.team_id)
            )

            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Active dispatch record not found."
                )

            cur.execute(
                """
                UPDATE DistressTickets
                SET status = 'Resolved'
                WHERE token_id = %s
                  AND status = 'Dispatched'
                """,
                (payload.token_id,)
            )

            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=409,
                    detail="Victim ticket is not in the expected state."
                )

            cur.execute(
                """
                UPDATE RescueTeams
                SET status = 'Available'
                WHERE team_id = %s
                  AND status = 'In_Transit'
                """,
                (payload.team_id,)
            )

            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=409,
                    detail="Rescue team is not in the expected state."
                )

        conn.commit()

        return {
            "status": "Success",
            "message": (
                f"Rescue operation for {payload.token_id} completed. "
                f"Team {payload.team_id} is now available."
            )
        }

    except HTTPException:
        if conn:
            conn.rollback()
        raise

    except Exception as e:
        if conn:
            conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        ) from e

    finally:
        if conn:
            conn.close()