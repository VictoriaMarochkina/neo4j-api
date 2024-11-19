from fastapi.testclient import TestClient
from api import app
import pytest
from dotenv import load_dotenv
import os

load_dotenv()

client = TestClient(app)

API_TOKEN = os.getenv("API_TOKEN")


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        os.getenv("DATABASE_URL"), auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    yield
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    driver.close()


def test_get_all_users_empty():
    response = client.get("/users/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_user():
    user_data = {
        "user_id": 1,
        "name": "Test User",
        "sex": 1,
        "home_town": "Test Town",
        "city": "Test City",
        "subscriptions": [],
        "follows": []
    }
    response = client.post("/users/", json=user_data, headers={"token": API_TOKEN})
    assert response.status_code == 200
    assert response.json()["message"] == "User 1 created"


def test_get_all_users_after_add():
    response = client.get("/users/")
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 1
    assert users[0]["id"] == 1
    assert users[0]["name"] == "Test User"


def test_get_user_relationships_empty():
    response = client.get("/users/1/relationships/")
    assert response.status_code == 200
    assert response.json()["relationships"] == []


def test_create_group():
    group_data = {
        "group_id": 1,
        "name": "Test Group",
        "subscribers": []
    }
    response = client.post("/groups/", json=group_data, headers={"token": API_TOKEN})
    assert response.status_code == 200
    assert response.json()["message"] == "Group 1 created"


def test_get_all_groups_after_add():
    response = client.get("/groups/")
    assert response.status_code == 200
    groups = response.json()
    assert len(groups) == 1
    assert groups[0]["id"] == 1
    assert groups[0]["name"] == "Test Group"


def test_user_subscription_to_group():
    user_data = {
        "user_id": 2,
        "name": "User Subscriber",
        "sex": 1,
        "home_town": "Town A",
        "city": "City A",
        "subscriptions": [1],
        "follows": []
    }
    response = client.post("/users/", json=user_data, headers={"token": API_TOKEN})
    assert response.status_code == 200
    assert response.json()["message"] == "User 2 created"

    response = client.get("/users/2/relationships/")
    assert response.status_code == 200
    relationships = response.json()["relationships"]
    assert len(relationships) == 1
    assert relationships[0]["group_id"] == 1
    assert relationships[0]["name"] == "Test Group"
    assert relationships[0]["relationship"] == "Subscribe"


def test_group_with_subscriber():
    group_data = {
        "group_id": 2,
        "name": "Group with Subscriber",
        "subscribers": [2]
    }
    response = client.post("/groups/", json=group_data, headers={"token": API_TOKEN})
    assert response.status_code == 200
    assert response.json()["message"] == "Group 2 created"

    response = client.get("/groups/2/relationships/")
    assert response.status_code == 200
    subscribers = response.json()["relationships"]
    assert len(subscribers) == 1
    assert subscribers[0]["user_id"] == 2
    assert subscribers[0]["name"] == "User Subscriber"


def test_user_follow_user():
    user_data_1 = {
        "user_id": 3,
        "name": "User A",
        "sex": 1,
        "home_town": "Town B",
        "city": "City B",
        "subscriptions": [],
        "follows": []
    }
    user_data_2 = {
        "user_id": 4,
        "name": "User B",
        "sex": 2,
        "home_town": "Town C",
        "city": "City C",
        "subscriptions": [],
        "follows": []
    }

    client.post("/users/", json=user_data_1, headers={"token": API_TOKEN})
    client.post("/users/", json=user_data_2, headers={"token": API_TOKEN})

    follow_data = {
        "user_id": 3,
        "name": "User A",
        "sex": 1,
        "home_town": "Town B",
        "city": "City B",
        "subscriptions": [],
        "follows": [4]
    }
    response = client.post("/users/", json=follow_data, headers={"token": API_TOKEN})
    assert response.status_code == 200

    response = client.get("/users/3/relationships/")
    assert response.status_code == 200
    relationships = response.json()["relationships"]
    assert len(relationships) == 1
    assert relationships[0]["user_id"] == 4
    assert relationships[0]["name"] == "User B"
    assert relationships[0]["relationship"] == "Follow"
