from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.store import models, schemas


# Category CRUD
async def get_category_by_id(
    db: AsyncSession, category_id: int
) -> Optional[models.Category]:
    result = await db.execute(
        select(models.Category).where(models.Category.id == category_id)
    )
    return result.scalar_one_or_none()


async def get_categories(db: AsyncSession) -> list[models.Category]:
    result = await db.execute(select(models.Category).order_by(models.Category.name))
    return list(result.scalars().all())


async def create_category(
    db: AsyncSession, category_in: schemas.CategoryCreate
) -> models.Category:
    category = models.Category(**category_in.model_dump())
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


# Product CRUD
async def get_product_by_id(
    db: AsyncSession, product_id: int
) -> Optional[models.Product]:
    result = await db.execute(
        select(models.Product).where(models.Product.id == product_id)
    )
    return result.scalar_one_or_none()


async def get_products(
    db: AsyncSession,
    category_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[models.Product]:
    query = select(models.Product).where(models.Product.is_active)
    if category_id:
        query = query.where(models.Product.category_id == category_id)
    query = query.order_by(models.Product.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_product(
    db: AsyncSession, product_in: schemas.ProductCreate, seller_id: int
) -> models.Product:
    product = models.Product(**product_in.model_dump(), seller_id=seller_id)
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
) -> models.Product:
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
) -> list[models.CartItem]:
    query = select(models.CartItem)
    conditions = []
    if user_id:
        conditions.append(models.CartItem.user_id == user_id)
    if session_id:
        conditions.append(models.CartItem.session_id == session_id)
    if conditions:
        query = query.where(or_(*conditions))
    else:
        return []
    result = await db.execute(query.order_by(models.CartItem.created_at.desc()))
    return list(result.scalars().all())


async def get_cart_item_by_id(
    db: AsyncSession, item_id: int
) -> Optional[models.CartItem]:
    result = await db.execute(
        select(models.CartItem).where(models.CartItem.id == item_id)
    )
    return result.scalar_one_or_none()


async def add_to_cart(
    db: AsyncSession,
    product_id: int,
    quantity: int = 1,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
) -> models.CartItem:
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
    query = select(models.CartItem).where(models.CartItem.product_id == product_id)
    if user_id:
        query = query.where(models.CartItem.user_id == user_id)
    elif session_id:
        query = query.where(models.CartItem.session_id == session_id)
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
        cart_item = models.CartItem(
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
    query = select(models.CartItem)
    conditions = []
    if user_id:
        conditions.append(models.CartItem.user_id == user_id)
    if session_id:
        conditions.append(models.CartItem.session_id == session_id)
    if not conditions:
        return
    query = query.where(or_(*conditions))
    result = await db.execute(query)
    items = result.scalars().all()
    for item in items:
        await db.delete(item)
    await db.commit()


# Order CRUD
async def get_order_by_id(db: AsyncSession, order_id: int) -> Optional[models.Order]:
    result = await db.execute(select(models.Order).where(models.Order.id == order_id))
    return result.scalar_one_or_none()


async def get_user_orders(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
) -> list[models.Order]:
    result = await db.execute(
        select(models.Order)
        .where(models.Order.user_id == user_id)
        .order_by(models.Order.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_order_from_cart(
    db: AsyncSession, user_id: int, session_id: Optional[str] = None
) -> models.Order:
    # Get cart items
    cart_items = await get_cart_items(db, user_id=user_id, session_id=session_id)
    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty"
        )

    # Calculate total
    total_amount = Decimal("0")
    order_items_data = []
    for item in cart_items:
        if not item.product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {item.product.title} is not available",
            )
        item_total = item.product.price * item.quantity
        total_amount += item_total
        order_items_data.append(
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price_at_purchase": item.product.price,
            }
        )

    # Create order
    order = models.Order(user_id=user_id, total_amount=total_amount, status="pending")
    db.add(order)
    await db.flush()  # Get order.id

    # Create order items
    for item_data in order_items_data:
        order_item = models.OrderItem(order_id=order.id, **item_data)
        db.add(order_item)

    # Create purchases
    for item_data in order_items_data:
        purchase = models.Purchase(
            user_id=user_id,
            order_id=order.id,
            product_id=item_data["product_id"],
        )
        db.add(purchase)

    # Clear cart
    await clear_cart(db, user_id=user_id, session_id=session_id)

    await db.commit()
    await db.refresh(order)
    return order


async def update_order_status(
    db: AsyncSession, order_id: int, status: str, payment_id: Optional[str] = None
) -> models.Order:
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
) -> list[models.Purchase]:
    result = await db.execute(
        select(models.Purchase)
        .where(models.Purchase.user_id == user_id)
        .order_by(models.Purchase.purchased_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_purchase_content(
    db: AsyncSession, user_id: int, order_id: int
) -> list[schemas.PurchaseContentRead]:
    result = await db.execute(
        select(models.Purchase, models.Product)
        .join(models.Product, models.Purchase.product_id == models.Product.id)
        .where(
            and_(
                models.Purchase.user_id == user_id,
                models.Purchase.order_id == order_id,
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
        select(models.Purchase).where(
            and_(
                models.Purchase.user_id == user_id,
                models.Purchase.product_id == product_id,
            )
        )
    )
    return result.scalar_one_or_none() is not None


# Review CRUD
async def get_reviews_by_product(
    db: AsyncSession, product_id: int, skip: int = 0, limit: int = 100
) -> list[models.Review]:
    result = await db.execute(
        select(models.Review)
        .where(models.Review.product_id == product_id)
        .order_by(models.Review.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_review_by_id(db: AsyncSession, review_id: int) -> Optional[models.Review]:
    result = await db.execute(
        select(models.Review).where(models.Review.id == review_id)
    )
    return result.scalar_one_or_none()


async def create_review(
    db: AsyncSession, review_in: schemas.ReviewCreate, user_id: int, product_id: int
) -> models.Review:
    # Check if user has purchased the product
    has_purchased = await has_user_purchased_product(db, user_id, product_id)
    if not has_purchased:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only review products you have purchased",
        )

    # Check if review already exists
    existing = await db.execute(
        select(models.Review).where(
            and_(
                models.Review.user_id == user_id,
                models.Review.product_id == product_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this product",
        )

    review = models.Review(
        **review_in.model_dump(), user_id=user_id, product_id=product_id
    )
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
) -> models.Review:
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
