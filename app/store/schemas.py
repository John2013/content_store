from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# Category schemas
class CategoryBase(BaseModel):
    name: str = Field(max_length=100)
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryRead(CategoryBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# Product schemas
class ProductBase(BaseModel):
    title: str = Field(max_length=200)
    description: Optional[str] = None
    price: Decimal = Field(gt=0, decimal_places=2)
    content_text: str
    category_id: Optional[int] = None
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    content_text: Optional[str] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None


class ProductRead(BaseModel):
    id: int
    title: str
    description: Optional[str]
    price: Decimal
    category_id: Optional[int]
    seller_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryRead] = None

    model_config = {"from_attributes": True}


class ProductDetailRead(ProductRead):
    """Product with full details but without content_text (content is accessed via purchase endpoint)."""

    pass


# CartItem schemas
class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, default=1)
    session_id: Optional[str] = None


class CartItemRead(BaseModel):
    id: int
    product_id: int
    quantity: int
    created_at: datetime
    product: ProductRead

    model_config = {"from_attributes": True}


# Order schemas
class OrderCreate(BaseModel):
    session_id: Optional[str] = None


class OrderRead(BaseModel):
    id: int
    user_id: int
    total_amount: Decimal
    status: str
    payment_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    order_items: list["OrderItemRead"]

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    status: str = Field(pattern="^(pending|paid|cancelled)$")


# OrderItem schemas
class OrderItemRead(BaseModel):
    id: int
    order_id: int
    product_id: int
    quantity: int
    price_at_purchase: Decimal
    product: ProductRead

    model_config = {"from_attributes": True}


# Purchase schemas
class PurchaseRead(BaseModel):
    id: int
    user_id: int
    order_id: int
    product_id: int
    purchased_at: datetime
    product: ProductRead
    order: OrderRead

    model_config = {"from_attributes": True}


class PurchaseContentRead(BaseModel):
    """Content access for purchased product."""

    product_id: int
    product_title: str
    content_text: str
    purchased_at: datetime


# Review schemas
class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class ReviewRead(BaseModel):
    id: int
    user_id: int
    product_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime
    user: Optional["UserRead"] = None

    model_config = {"from_attributes": True}


# Forward reference for UserRead
from app.user.schemas import UserRead  # noqa: E402

ReviewRead.model_rebuild()
