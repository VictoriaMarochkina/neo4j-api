from neomodel import db
import pytest
from api.models import User, Group


@pytest.fixture(scope="module", autouse=True)
def clear_database():
    db.cypher_query("MATCH (n) DETACH DELETE n")
    yield
    db.cypher_query("MATCH (n) DETACH DELETE n")


def test_user_creation():
    user1 = User(user_id=1, name="User1", sex=1, home_town="Hometown1", city="City1").save()
    assert user1.user_id == 1
    assert user1.name == "User1"
    assert user1.sex == 1
    assert user1.home_town == "Hometown1"
    assert user1.city == "City1"


def test_group_creation():
    group1 = Group(group_id=1, name="Group1").save()
    assert group1.group_id == 1
    assert group1.name == "Group1"
    assert group1.subscribers_count == 0


def test_user_subscription_to_group():
    user2 = User(user_id=2, name="User2").save()
    group2 = Group(group_id=2, name="Group2").save()
    user2.subscriptions.connect(group2)

    assert user2.subscriptions.is_connected(group2)


def test_user_follow_another_user():
    user3 = User(user_id=3, name="User3").save()
    user4 = User(user_id=4, name="User4").save()
    user3.follows.connect(user4)

    assert user3.follows.is_connected(user4)

