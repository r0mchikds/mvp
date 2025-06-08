from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List
from sqlmodel import Session, select
from models.item import Item, ItemRead
from services.logging.logging import get_logger
from database.database import get_session
from auth.authenticate import authenticate


search_route = APIRouter()
logger = get_logger(__name__)

@search_route.post("/by_ids", response_model=List[ItemRead])
def get_items_by_ids(
    item_ids: List[int] = Body(..., embed=True),
    session: Session = Depends(get_session),
    user_email: str = Depends(authenticate)
):
    """
    Получение списка товаров по их item_id.
    Используется для отображения карточек после сортировки.
    """
    try:
        logger.info(f"Received item_ids: {item_ids}")
        if not item_ids:
            return []
        statement = select(Item).where(Item.id.in_(item_ids))
        items = session.exec(statement).all()

        # Сохраняем порядок, соответствующий item_ids
        id_to_item = {item.id: item for item in items}
        ordered = [id_to_item[i] for i in item_ids if i in id_to_item]

        return ordered

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load items: {str(e)}")
