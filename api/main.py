import os
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
from neo4j import GraphDatabase, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("DATABASE_URL")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
API_TOKEN = os.getenv("API_TOKEN")

if not all([NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, API_TOKEN]):
    raise ValueError("Убедитесь, что все переменные окружения указаны")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_token(token: str = Header(...)):
    if token != API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


class UserRequest(BaseModel):
    user_id: int
    name: str
    sex: int
    home_town: str
    city: str
    subscriptions: Optional[List[int]] = []
    follows: Optional[List[int]] = []


class GroupRequest(BaseModel):
    group_id: int
    name: str
    subscribers: Optional[List[int]] = []


@app.on_event("shutdown")
async def shutdown():
    driver.close()


@app.get("/users/")
async def get_all_users():
    query = Query("""
    MATCH (u:User)
    RETURN u.user_id AS id, u.name AS name, u.sex AS sex, u.home_town AS home_town, u.city AS city
    """)
    with driver.session() as session:
        result = session.run(query)
        users = [record.data() for record in result]
    return users


@app.get("/users/{user_id}/relationships/")
async def get_user_relationships(user_id: int):
    query = Query(
        """
        MATCH (u:User {user_id: $user_id})
        OPTIONAL MATCH (u)-[:Subscribe]->(g:Group)
        OPTIONAL MATCH (u)-[:Follow]->(followed:User)
        OPTIONAL MATCH (follower:User)-[:Follow]->(u)
        RETURN
            [x IN COLLECT(DISTINCT {group_id: g.group_id, name: g.name, relationship: "Subscribe"}) WHERE x.group_id IS NOT NULL] AS subscriptions,
            [x IN COLLECT(DISTINCT {user_id: followed.user_id, name: followed.name, relationship: "Follow"}) WHERE x.user_id IS NOT NULL] AS outgoing_follows,
            [x IN COLLECT(DISTINCT {user_id: follower.user_id, name: follower.name, relationship: "Follow"}) WHERE x.user_id IS NOT NULL] AS incoming_follows
        """
    )
    with driver.session() as session:
        result = session.run(query, user_id=user_id)
        record = result.single()
        if not record:
            raise HTTPException(status_code=404, detail="User not found")

        combined_relationships = []
        if record["subscriptions"]:
            combined_relationships += record["subscriptions"]
        if record["outgoing_follows"]:
            combined_relationships += record["outgoing_follows"]
        if record["incoming_follows"]:
            combined_relationships += record["incoming_follows"]

        if not combined_relationships:
            return {"relationships": []}

        return {"relationships": combined_relationships}


# Создание пользователя
@app.post("/users/", dependencies=[Depends(get_token)])
async def create_user(user_request: UserRequest):
    create_user_query = Query("""
    MERGE (u:User {user_id: $user_id})
    SET u.name = $name, u.sex = $sex, u.home_town = $home_town, u.city = $city
    """)
    with driver.session() as session:
        session.run(create_user_query, **user_request.dict())
        for group_id in user_request.subscriptions:
            session.run(
                Query("""
                MATCH (u:User {user_id: $user_id}), (g:Group {group_id: $group_id})
                MERGE (u)-[:Subscribe]->(g)
                """),
                user_id=user_request.user_id,
                group_id=group_id,
            )
        for follow_id in user_request.follows:
            session.run(
                Query("""
                MATCH (u:User {user_id: $user_id}), (f:User {user_id: $follow_id})
                MERGE (u)-[:Follow]->(f)
                """),
                user_id=user_request.user_id,
                follow_id=follow_id,
            )
    return {"message": f"User {user_request.user_id} created"}


@app.delete("/users/{user_id}", dependencies=[Depends(get_token)])
async def delete_user(user_id: int):
    query = Query("""
    MATCH (u:User {user_id: $user_id})
    DETACH DELETE u
    """)
    with driver.session() as session:
        session.run(query, user_id=user_id)
    return {"message": f"User {user_id} deleted"}


@app.get("/groups/")
async def get_all_groups():
    query = Query("""
    MATCH (g:Group)
    RETURN g.group_id AS id, g.name AS name, g.subscribers_count AS subscribers_count
    """)
    with driver.session() as session:
        result = session.run(query)
        groups = [
            {
                "id": record["id"],
                "name": record["name"],
                "subscribers_count": record["subscribers_count"]
            }
            for record in result
        ]
    return groups


@app.get("/groups/{group_id}/relationships/")
async def get_group_relationships(group_id: int):
    query = Query("""
    MATCH (g:Group {group_id: $group_id})
    OPTIONAL MATCH (u:User)-[:Subscribe]->(g)
    RETURN COLLECT(DISTINCT {user_id: u.user_id, name: u.name}) AS subscribers
    """)
    with driver.session() as session:
        result = session.run(query, group_id=group_id)
        record = result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Group not found")

        subscribers = [
            subscriber for subscriber in record["subscribers"]
            if subscriber["user_id"] is not None and subscriber["name"] is not None
        ]
        return {"group_id": group_id, "relationships": subscribers}


@app.post("/groups/", dependencies=[Depends(get_token)])
async def create_group(group_request: GroupRequest):
    create_group_query = Query("""
    MERGE (g:Group {group_id: $group_id})
    SET g.name = $name
    """)
    with driver.session() as session:
        session.run(create_group_query, **group_request.dict())
        for user_id in group_request.subscribers:
            session.run(
                Query("""
                MATCH (u:User {user_id: $user_id}), (g:Group {group_id: $group_id})
                MERGE (u)-[:Subscribe]->(g)
                """),
                user_id=user_id,
                group_id=group_request.group_id,
            )
    return {"message": f"Group {group_request.group_id} created"}


@app.delete("/groups/{group_id}", dependencies=[Depends(get_token)])
async def delete_group(group_id: int):
    query = Query("""
    MATCH (g:Group {group_id: $group_id})
    DETACH DELETE g
    """)
    with driver.session() as session:
        session.run(query, group_id=group_id)
    return {"message": f"Group {group_id} deleted"}
