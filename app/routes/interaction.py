from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from models.interaction import Interaction, InteractionCreate
from models.user import User
from models.item import Item
from database.database import get_session
from auth.authenticate import authenticate
from typing import Optional
import numpy as np
import json


interaction_route = APIRouter()

@interaction_route.post("/like")
def like_interaction(data: InteractionCreate, session: Session = Depends(get_session)):
    """
    Обработка лайка пользователя к товару и пересчёт эмбеддинга.
    Если у пользователя ещё нет embedding — он создаётся по первому лайку.
    """
    try:
        # Проверяем, был ли уже лайк
        interaction = session.get(Interaction, (data.user_id, data.item_id))
        if interaction:
            interaction.liked = True
        else:
            interaction = Interaction(**data.dict(), liked=True)
            session.add(interaction)
        session.commit()

        # Находим все embedding лайкнутых товаров
        stmt = select(Item.embedding).join(Interaction).where(
            Interaction.user_id == data.user_id,
            Interaction.liked == True,
            Item.embedding != None
        )
        embeddings = session.exec(stmt).all()

        if embeddings:
            vectors = np.array([json.loads(e) for e in embeddings])
            new_emb = np.mean(vectors, axis=0).tolist()

            user = session.get(User, data.user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            user.embedding = json.dumps(new_emb)
            session.add(user)
            session.commit()

            return {"message": "Like saved. User embedding updated."}
        else:
            return {"message": "Like saved. No embeddings available to update user."}

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
