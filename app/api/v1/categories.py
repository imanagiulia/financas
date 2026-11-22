from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Category
from schemas import CategoryCreate, CategoryOut
from auth import AuthUser, get_current_user

router = APIRouter()


@router.get("", response_model=List[CategoryOut])
def list_categories(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Category)
        .filter(Category.user_id == current_user.id)
        .order_by(Category.name.asc())
        .all()
    )


@router.post("", response_model=CategoryOut)
def create_category(
    data: CategoryCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cat = Category(user_id=current_user.id, **data.model_dump())
    db.add(cat)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ja existe uma categoria com esse nome.")
    db.refresh(cat)
    return cat


@router.put("/{cat_id}", response_model=CategoryOut)
def update_category(
    cat_id: int,
    data: CategoryCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cat = (
        db.query(Category)
        .filter(Category.id == cat_id, Category.user_id == current_user.id)
        .first()
    )
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria nao encontrada")
    for k, v in data.model_dump().items():
        setattr(cat, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ja existe uma categoria com esse nome.")
    db.refresh(cat)
    return cat


@router.delete("/{cat_id}")
def delete_category(
    cat_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cat = (
        db.query(Category)
        .filter(Category.id == cat_id, Category.user_id == current_user.id)
        .first()
    )
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria nao encontrada")
    db.delete(cat)
    db.commit()
    return {"ok": True}
