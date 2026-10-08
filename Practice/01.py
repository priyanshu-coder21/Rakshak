# Q1. Health Check API

# Your FastAPI application needs an endpoint that allows the frontend to check whether the server is running.

# Requirement:

# * Endpoint: GET /health
# * It should return:
#       {
#           "status": "running"
#       }

# from fastapi import FastAPI, HTTPException


# app = FastAPI()

# @app.get('/health')
# def healthCheck():
#     return { "status": "running"}




# @app.get('/')
# def welcome():
#     return {"message": "Welcome this this API"}







# @app.get('/info')
# def info():
#     return {
#         "name": "Disaster Relief System",
#         "version": "1.0",
#         "status": "active"
#     }













# @app.get('/rescue-teams/{team_id}')
# def get_recue_team(team_id: int):
#     return {
#         "team_id": id,
#         "message": "Rescue team retrieved successfully"
#     }













# @app.get('/distress/{ticket_id}')
# def get_distress_ticket(ticket_id: int):
#     return {
#         "ticket_id": ticket_id,
#         "status": "received"
#     }










from fastapi import FastAPI, HTTPException
import psycopg2
import os

app = FastAPI()

@app.get('/rescue-teams/')
async def rescue_team(status: str):

    connection = None
    cursor = None

    try:

        connection = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT")
        )

        cursor = connection.cursor()

        query = """
            SELECT team_id, team_name, members, status, location
            FROM rescue_teams
            WHERE status = %s
        """

        cursor.execute(query, (status,))

        rows = cursor.fetchall()

        if not rows:
            raise HTTPException(
                status=500,
                detail="Database not found."
            )

        result = []
        for row in rows:
            result.append({
                "team_id": row[0],
                "team_name": row[1],
                "members": row[2],
                "status": row[3],
                "location": row[4]
            })
        
        return result

    except:
        raise HTTPException (
            status= 404,
            detail="No rescue teams found with requested status"
        )