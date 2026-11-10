"""shop_routes.py - REST API for the ZenithMart storefront."""
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import shop_db as db

router = APIRouter(prefix="/api")

class Item(BaseModel):
    product_id: str = Field(max_length=20)
    qty: int = Field(ge=1, le=10)
    size: str = Field(default="", max_length=4)

class OrderIn(BaseModel):
    cust: str = Field(min_length=8, max_length=64)
    name: str = Field(min_length=2, max_length=60)
    phone: str = Field(pattern=r"^\d{10}$")
    address: str = Field(min_length=5, max_length=200)
    city: str = Field(min_length=2, max_length=60)
    pincode: str = Field(pattern=r"^\d{6}$")
    shipping: str = Field(pattern="^(standard|fast)$")
    items: List[Item] = Field(min_length=1, max_length=20)

class RequestIn(BaseModel):
    cust: str = Field(min_length=8, max_length=64)
    kind: str = Field(pattern="^(cancel|return|exchange)$")
    reason: str = Field(min_length=3, max_length=300)

class Cust(BaseModel):
    cust: str = Field(min_length=8, max_length=64)

@router.get("/products")
def list_products(q: str = "", category: str = "", lo: int = 0, hi: int = 1000000, sort: str = ""):
    return db.products(q.strip()[:60], category, lo, hi, sort)

@router.get("/products/{pid}")
def get_product(pid: str):
    p = db.product(pid)
    if not p: raise HTTPException(404, "Product not found")
    return p

@router.post("/orders")
def create_order(o: OrderIn):
    try:
        oid = db.place_order(o.cust, o.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"order_id": oid}

@router.get("/orders")
def my_orders(cust: str):
    return db.orders(cust)

@router.get("/orders/{oid}")
def get_order(oid: str, cust: str):
    o = db.order(oid, cust)
    if not o: raise HTTPException(404, "Order not found")
    return o

@router.post("/orders/{oid}/advance")
def advance(oid: str, b: Cust):
    try: db.advance(oid, b.cust)
    except ValueError as e: raise HTTPException(400, str(e))
    return db.order(oid, b.cust)

@router.post("/orders/{oid}/request")
def request(oid: str, b: RequestIn):
    try: db.add_request(oid, b.cust, b.kind, b.reason)
    except ValueError as e: raise HTTPException(400, str(e))
    return db.order(oid, b.cust)