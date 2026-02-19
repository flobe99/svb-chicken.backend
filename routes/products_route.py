from fastapi import Depends, HTTPException, Query, APIRouter
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
from datetime import UTC, datetime, timedelta
from sqlalchemy import DateTime, cast
from database import SessionLocal, get_db
# from app import SessionLocal
from helper import check_slot_limit
from models import *
from routes.websocket import broadcast_order_event

products_router = APIRouter(
    # prefix="/users",
    tags=["Products"]
)

@products_router.get("/products", tags=["Products"])
def get_products(db: Session = Depends(get_db)):
    """
    Retrieves all available products.

    Returns:
        list: A list of product dictionaries.
    """
    try:
        products = db.query(ProductDB).order_by(ProductDB.id.asc()).all()
        return [product.__dict__ for product in products]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@products_router.get("/product/{id}", tags=["Products"])
def get_product(id: int, db: Session = Depends(get_db)):
    """
    Retrieves a single product by its ID.

    Args:
        id (int): The ID of the product to retrieve.

    Returns:
        dict: The product data.
    """
    try:
        product = db.query(ProductDB).filter(ProductDB.id == id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product.__dict__
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@products_router.post("/product", tags=["Products"])
def create_product(product: Product, db: Session = Depends(get_db)):
    """
    Creates a new product entry.

    Args:
        product (Product): The product data to store.

    Returns:
        dict: The created product data.
    """
    db_product = ProductDB(**{k: v for k, v in product.model_dump().items() if k != "id"})
    try:
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product.__dict__
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@products_router.put("/product/{id}", tags=["Products"])
def update_product(id: int, updated_product: Product, db: Session = Depends(get_db)):
    """
    Updates an existing product.

    Args:
        id (int): The ID of the product to update.
        updated_product (Product): The new product data.

    Returns:
        dict: A success flag and the updated product data.
    """
    try:
        product = db.query(ProductDB).filter(ProductDB.id == id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        product.product = updated_product.product
        product.price = updated_product.price

        db.commit()
        db.refresh(product)

        return {
            "success": True,
            "product": {
                "id": product.id,
                "product": product.product,
                "price": float(product.price),
                "name": product.name,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }

@products_router.delete("/product/{id}", tags=["Products"])
def delete_product(id: int, db: Session = Depends(get_db)):
    """
    Deletes a product by its ID.

    Args:
        id (int): The ID of the product to delete.

    Returns:
        dict: A success flag if deletion was successful.
    """
    
    try:
        product = db.query(ProductDB).filter(ProductDB.id == id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        db.delete(product)
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))