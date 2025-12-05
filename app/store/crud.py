from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, and_, or_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.store import schemas
from app.store.models import (
    Order,
    CartItem,
    OrderItem,
    Category,
    Product,
    Purchase,
    Review,
)
from app.user import schemas as user_schemas


# Category CRUD
async def get_category_by_id(db: AsyncSession, category_id: int) -> Optional[Category]:
    result = await db.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()


async def get_categories(db: AsyncSession) -> list[Category]:
    result = await db.execute(select(Category).order_by(Category.name))
    return list(result.scalars().all())


async def create_category(
    db: AsyncSession,
    category_in: schemas.CategoryCreate,
    current_user: user_schemas.UserRead,
) -> Category:
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to create a category",
        )
    category = Category(**category_in.model_dump())
    db.add(category)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists",
        )
    await db.refresh(category)
    return category


async def delete_category(
    db: AsyncSession, category_id: int, current_user: user_schemas.UserRead
) -> None:
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to create a category",
        )
    category = await get_category_by_id(db, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="category not found"
        )
    await db.delete(category)
    await db.commit()


# Product CRUD
async def get_product_by_id(db: AsyncSession, product_id: int) -> Optional[Product]:
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def get_products(
    db: AsyncSession,
    category_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Product]:
    query = select(Product).where(Product.is_active)
    if category_id:
        query = query.where(Product.category_id == category_id)
    query = query.order_by(Product.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_product(
    db: AsyncSession, product_in: schemas.ProductCreate
) -> Product:
    product = Product(**product_in.model_dump())
    db.add(product)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error creating product",
        )
    await db.refresh(product)
    return product


async def update_product(
    db: AsyncSession, product_id: int, product_in: schemas.ProductUpdate
) -> Product:
    product = await get_product_by_id(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    update_data = product_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def delete_product(db: AsyncSession, product_id: int) -> None:
    product = await get_product_by_id(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    await db.delete(product)
    await db.commit()


# CartItem CRUD
async def get_cart_items(
    db: AsyncSession, user_id: Optional[int] = None, session_id: Optional[str] = None
) -> list[CartItem]:
    query = select(CartItem)
    conditions = []
    if user_id:
        conditions.append(CartItem.user_id == user_id)
    if session_id:
        conditions.append(CartItem.session_id == session_id)
    if conditions:
        query = query.options(selectinload(CartItem.product)).where(or_(*conditions))
    else:
        return []
    result = await db.execute(query.order_by(CartItem.created_at.desc()))
    return list(result.scalars().all())


async def get_cart_item_by_id(db: AsyncSession, item_id: int) -> Optional[CartItem]:
    result = await db.execute(select(CartItem).where(CartItem.id == item_id))
    return result.scalar_one_or_none()


async def add_to_cart(
    db: AsyncSession,
    product_id: int,
    quantity: int = 1,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
) -> CartItem:
    # Check if product exists
    product = await get_product_by_id(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Product is not active"
        )

    # Check if item already in cart
    query = select(CartItem).where(CartItem.product_id == product_id)
    if user_id:
        query = query.where(CartItem.user_id == user_id)
    elif session_id:
        query = query.where(CartItem.session_id == session_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either user_id or session_id must be provided",
        )

    existing = await db.execute(query)
    existing_item = existing.scalar_one_or_none()

    if existing_item:
        existing_item.quantity += quantity
        db.add(existing_item)
    else:
        cart_item = CartItem(
            product_id=product_id,
            quantity=quantity,
            user_id=user_id,
            session_id=session_id,
        )
        db.add(cart_item)
        existing_item = cart_item

    await db.commit()
    await db.refresh(existing_item)
    return existing_item


async def remove_from_cart(db: AsyncSession, item_id: int) -> None:
    item = await get_cart_item_by_id(db, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found"
        )
    await db.delete(item)
    await db.commit()


async def clear_cart(
    db: AsyncSession, user_id: Optional[int] = None, session_id: Optional[str] = None
) -> None:
    query = select(CartItem)
    conditions = []
    if user_id:
        conditions.append(CartItem.user_id == user_id)
    if session_id:
        conditions.append(CartItem.session_id == session_id)
    if not conditions:
        return
    query = query.where(or_(*conditions))
    result = await db.execute(query)
    items = result.scalars().all()
    for item in items:
        await db.delete(item)
    await db.commit()


# Order CRUD
async def get_order_by_id(db: AsyncSession, order_id: int) -> Optional[Order]:
    result = await db.execute(select(Order).where(Order.id == order_id))
    return result.scalar_one_or_none()


async def get_user_orders(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
) -> list[Order]:
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_order_from_cart(
    db: AsyncSession, user_id: int, session_id: str = None
) -> Order:
    # Fetch cart items with products and their categories
    cart_stmt = (
        select(CartItem)
        .where(
            (CartItem.user_id == user_id)
            if user_id
            else (CartItem.session_id == session_id)
        )
        .options(selectinload(CartItem.product).selectinload(Product.category))
    )
    cart_result = await db.execute(cart_stmt)
    cart_items = cart_result.scalars().all()

    if not cart_items:
        raise ValueError("Cart is empty")

    total_amount = Decimal(
        sum(item.product.price * item.quantity for item in cart_items)
    )

    # Create order
    order = Order(user_id=user_id, total_amount=total_amount)
    db.add(order)
    await db.flush()

    # Create order items
    for cart_item in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            price_at_purchase=cart_item.product.price,
        )
        db.add(order_item)

    # Remove cart items
    delete_stmt = delete(CartItem).where(
        (CartItem.user_id == user_id)
        if user_id
        else (CartItem.session_id == session_id)
    )
    await db.execute(delete_stmt)

    # Re-fetch order with full relationships eager-loaded
    order_stmt = (
        select(Order)
        .where(Order.id == order.id)
        .options(
            selectinload(Order.order_items)
            .selectinload(OrderItem.product)
            .selectinload(Product.category),
            selectinload(Order.user),
        )
    )
    result = await db.execute(order_stmt)
    order = result.scalar_one()

    await db.commit()
    return order


async def update_order_status(
    db: AsyncSession, order_id: int, status: str, payment_id: Optional[str] = None
) -> Order:
    order = await get_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    order.status = status
    if payment_id:
        order.payment_id = payment_id
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


# Purchase CRUD
async def get_user_purchases(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
) -> list[Purchase]:
    result = await db.execute(
        select(Purchase)
        .where(Purchase.user_id == user_id)
        .options(selectinload(Purchase.order).selectinload(Order.order_items))
        .order_by(Purchase.purchased_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_purchase_content(
    db: AsyncSession, user_id: int, order_id: int
) -> list[schemas.PurchaseContentRead]:
    result = await db.execute(
        select(Purchase, Product)
        .join(Product, Purchase.product_id == Product.id)
        .where(
            and_(
                Purchase.user_id == user_id,
                Purchase.order_id == order_id,
            )
        )
    )
    purchases = result.all()
    return [
        schemas.PurchaseContentRead(
            product_id=purchase.product_id,
            product_title=product.title,
            content_text=product.content_text,
            purchased_at=purchase.purchased_at,
        )
        for purchase, product in purchases
    ]


async def has_user_purchased_product(
    db: AsyncSession, user_id: int, product_id: int
) -> bool:
    result = await db.execute(
        select(Purchase).where(
            and_(
                Purchase.user_id == user_id,
                Purchase.product_id == product_id,
            )
        )
    )
    return result.scalar_one_or_none() is not None


# Review CRUD
async def get_reviews_by_product(
    db: AsyncSession, product_id: int, skip: int = 0, limit: int = 100
) -> list[Review]:
    result = await db.execute(
        select(Review)
        .where(Review.product_id == product_id)
        .order_by(Review.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_review_by_id(db: AsyncSession, review_id: int) -> Optional[Review]:
    result = await db.execute(select(Review).where(Review.id == review_id))
    return result.scalar_one_or_none()


async def create_review(
    db: AsyncSession, review_in: schemas.ReviewCreate, user_id: int, product_id: int
) -> Review:
    # Check if user has purchased the product
    has_purchased = await has_user_purchased_product(db, user_id, product_id)
    if not has_purchased:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only review products you have purchased",
        )

    # Check if review already exists
    existing = await db.execute(
        select(Review).where(
            and_(
                Review.user_id == user_id,
                Review.product_id == product_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this product",
        )

    review = Review(**review_in.model_dump(), user_id=user_id, product_id=product_id)
    db.add(review)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error creating review"
        )
    await db.refresh(review)
    return review


async def update_review(
    db: AsyncSession, review_id: int, review_in: schemas.ReviewUpdate, user_id: int
) -> Review:
    review = await get_review_by_id(db, review_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )
    if review.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own reviews",
        )
    update_data = review_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(review, field, value)
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


async def delete_review(db: AsyncSession, review_id: int, user_id: int) -> None:
    review = await get_review_by_id(db, review_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )
    if review.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own reviews",
        )
    await db.delete(review)
    await db.commit()
