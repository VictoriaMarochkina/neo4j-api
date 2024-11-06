import os
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
from .models import User, Group
from neomodel import config
from dotenv import load_dotenv

load_dotenv()

config.DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

API_TOKEN = os.getenv("API_TOKEN")


def get_token(token: str = Header(...)):
    if token != API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


class UserRequest(BaseModel):
    user_id: int
    name: str
    subscriptions: Optional[List[int]] = []  # Список групп, на которые подписан пользователь
    follows: Optional[List[int]] = []  # Список пользователей, на которых подписан пользователь


class GroupRequest(BaseModel):
    group_id: int
    name: str
    subscribers: Optional[List[int]] = []  # Список пользователей, подписанных на группу


class NodeResponse(BaseModel):
    id: int
    name: str


def update_relationships(user: User, subscriptions: List[int], follows: List[int]):
    # Обновление подписок на группы
    for group_id in subscriptions:
        group = Group.nodes.get_or_none(group_id=group_id)
        if group:
            user.subscriptions.connect(group)
        else:
            raise HTTPException(status_code=404, detail=f"Group {group_id} not found")

    # Обновление подписок на других пользователей
    for follow_id in follows:
        followed_user = User.nodes.get_or_none(user_id=follow_id)
        if followed_user:
            user.follows.connect(followed_user)
        else:
            raise HTTPException(status_code=404, detail=f"User {follow_id} not found")


@app.get("/users/", response_model=List[NodeResponse])
async def get_all_users():
    users = User.nodes.all()
    return [{"id": user.user_id, "name": user.name} for user in users]


@app.get("/users/{user_id}/relationships/")
async def get_user_relationships(user_id: int):
    user = User.nodes.get_or_none(user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    relationships = [{"group_id": group.group_id, "name": group.name, "relationship": "Subscribe"} for group in user.subscriptions.all()]
    relationships += [{"user_id": followed.user_id, "name": followed.name, "relationship": "Follow"} for followed in user.follows.all()]
    return {"user_id": user.user_id, "name": user.name, "relationships": relationships}


@app.post("/users/", dependencies=[Depends(get_token)])
async def create_user(user_request: UserRequest):
    existing_user = User.nodes.get_or_none(user_id=user_request.user_id)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(user_id=user_request.user_id, name=user_request.name).save()

    update_relationships(user, user_request.subscriptions, user_request.follows)

    return {"message": f"User {user.user_id} created with name {user.name}"}


@app.patch("/users/{user_id}", dependencies=[Depends(get_token)])
async def update_user(user_id: int, user_request: UserRequest):
    user = User.nodes.get_or_none(user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_relationships(user, user_request.subscriptions, user_request.follows)

    return {"message": f"User {user.user_id} updated with new relationships"}


@app.delete("/users/{user_id}", dependencies=[Depends(get_token)])
async def delete_user(user_id: int):
    user = User.nodes.get_or_none(user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.delete()
    return {"message": f"User {user_id} and all its relationships deleted"}


# Маршруты для работы с группами

@app.get("/groups/", response_model=List[NodeResponse])
async def get_all_groups():
    groups = Group.nodes.all()
    return [{"id": group.group_id, "name": group.name} for group in groups]


@app.get("/groups/{group_id}/relationships/")
async def get_group_relationships(group_id: int):
    group = Group.nodes.get_or_none(group_id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    relationships = [{"user_id": user.user_id, "name": user.name, "relationship": "Subscribe"} for user in group.subscribed_by.all()]
    return {"group_id": group.group_id, "name": group.name, "relationships": relationships}


@app.post("/groups/", dependencies=[Depends(get_token)])
async def create_group(group_request: GroupRequest):
    existing_group = Group.nodes.get_or_none(group_id=group_request.group_id)
    if existing_group:
        raise HTTPException(status_code=400, detail="Group already exists")

    group = Group(group_id=group_request.group_id, name=group_request.name).save()

    for user_id in group_request.subscribers:
        user = User.nodes.get_or_none(user_id=user_id)
        if user:
            user.subscriptions.connect(group)
        else:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return {"message": f"Group {group.group_id} created with name {group.name}"}


@app.delete("/groups/{group_id}", dependencies=[Depends(get_token)])
async def delete_group(group_id: int):
    group = Group.nodes.get_or_none(group_id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    group.delete()
    return {"message": f"Group {group_id} and all its relationships deleted"}
