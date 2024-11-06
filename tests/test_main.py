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
    from neomodel import db
    db.cypher_query("MATCH (n) DETACH DELETE n")
    yield
    db.cypher_query("MATCH (n) DETACH DELETE n")


def test_get_all_users_empty():
    response = client.get("/users/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_user():
    user_data = {
        "user_id": 1,
        "name": "Test User",
        "subscriptions": []
    }
    response = client.post("/users/", json=user_data, headers={"token": API_TOKEN})
    assert response.status_code == 200
    assert response.json()["message"] == "User 1 created with name Test User"


def test_get_all_users_after_add():
    response = client.get("/users/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == 1
    assert response.json()[0]["name"] == "Test User"


def test_get_user_relationships_empty():
    response = client.get("/users/1/relationships/")
    assert response.status_code == 200
    assert response.json()["relationships"] == []


def test_delete_user():
    response = client.delete("/users/1", headers={"token": API_TOKEN})
    assert response.status_code == 200
    assert response.json()["message"] == "User 1 and all its relationships deleted"


def test_get_all_users_after_delete():
    response = client.get("/users/")
    assert response.status_code == 200
    assert response.json() == []


def test_get_all_groups_empty():
    response = client.get("/groups/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_group():
    group_data = {
        "group_id": 1,
        "name": "Test Group",
        "subscribers": []
    }
    response = client.post("/groups/", json=group_data, headers={"token": API_TOKEN})
    assert response.status_code == 200
    assert response.json()["message"] == "Group 1 created with name Test Group"


def test_get_all_groups_after_add():
    response = client.get("/groups/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == 1
    assert response.json()[0]["name"] == "Test Group"


def test_get_group_relationships_empty():
    response = client.get("/groups/1/relationships/")
    assert response.status_code == 200
    assert response.json()["relationships"] == []


def test_delete_group():
    response = client.delete("/groups/1", headers={"token": API_TOKEN})
    assert response.status_code == 200
    assert response.json()["message"] == "Group 1 and all its relationships deleted"


def test_get_all_groups_after_delete():
    response = client.get("/groups/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_user_with_subscription():
    group_data = {"group_id": 2, "name": "Test Group 2", "subscribers": []}
    client.post("/groups/", json=group_data, headers={"token": API_TOKEN})

    user_data = {"user_id": 2, "name": "User with Subscription", "subscriptions": [2]}
    response = client.post("/users/", json=user_data, headers={"token": API_TOKEN})
    assert response.status_code == 200
    assert response.json()["message"] == "User 2 created with name User with Subscription"

    response = client.get("/users/2/relationships/")
    assert response.status_code == 200
    assert len(response.json()["relationships"]) == 1
    assert response.json()["relationships"][0]["group_id"] == 2
    assert response.json()["relationships"][0]["name"] == "Test Group 2"


def test_create_group_with_subscribers():
    user_data = {"user_id": 3, "name": "User for Group Subscription", "subscriptions": []}
    client.post("/users/", json=user_data, headers={"token": API_TOKEN})

    group_data = {"group_id": 3, "name": "Group with Subscribers", "subscribers": [3]}
    response = client.post("/groups/", json=group_data, headers={"token": API_TOKEN})
    assert response.status_code == 200
    assert response.json()["message"] == "Group 3 created with name Group with Subscribers"

    response = client.get("/groups/3/relationships/")
    assert response.status_code == 200
    assert len(response.json()["relationships"]) == 1
    assert response.json()["relationships"][0]["user_id"] == 3
    assert response.json()["relationships"][0]["name"] == "User for Group Subscription"


def test_user_follows_user():
    user_data_1 = {"user_id": 4, "name": "User Follower", "subscriptions": []}
    response = client.post("/users/", json=user_data_1, headers={"token": API_TOKEN})
    assert response.status_code == 200
    assert response.json()["message"] == "User 4 created with name User Follower"

    user_data_2 = {"user_id": 5, "name": "User Followed", "subscriptions": []}
    response = client.post("/users/", json=user_data_2, headers={"token": API_TOKEN})
    assert response.status_code == 200
    assert response.json()["message"] == "User 5 created with name User Followed"

    follow_data = {"user_id": 4, "name": "User Follower", "subscriptions": [], "follows": [5]}
    response = client.patch("/users/4", json=follow_data, headers={"token": API_TOKEN})
    assert response.status_code == 200
    assert response.json()["message"] == "User 4 updated with new relationships"

    response = client.get("/users/4/relationships/")
    assert response.status_code == 200
    relationships = response.json()["relationships"]

    follow_relationship = next((rel for rel in relationships if rel["user_id"] == 5), None)
    assert follow_relationship is not None
    assert follow_relationship["name"] == "User Followed"
    assert follow_relationship["relationship"] == "Follow"
