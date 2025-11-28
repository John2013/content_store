from typing import Annotated, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.store import crud, schemas
from app.user.routes import get_current_user
from app.user import schemas as user_schemas

router = APIRouter(prefix="/store", tags=["store"])


# Public endpoints
@router.get("/categories", response_model=list[schemas.CategoryRead])
async def get_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[schemas.CategoryRead]:
    """Get list of all categories."""
    categories = await crud.get_categories(db)
    return [schemas.CategoryRead.model_validate(c) for c in categories]


@router.get("/products", response_model=list[schemas.ProductRead])
async def get_products(
    db: Annotated[AsyncSession, Depends(get_db)],
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> list[schemas.ProductRead]:
    """Get list of products with optional category filter."""
    products = await crud.get_products(
        db, category_id=category_id, skip=skip, limit=limit
    )
    return [schemas.ProductRead.model_validate(p) for p in products]


@router.get("/products/{product_id}", response_model=schemas.ProductDetailRead)
async def get_product(
    product_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.ProductDetailRead:
    """Get product details (without content text)."""
    product = await crud.get_product_by_id(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return schemas.ProductDetailRead.model_validate(product)


@router.get("/products/{product_id}/reviews", response_model=list[schemas.ReviewRead])
async def get_product_reviews(
    product_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> list[schemas.ReviewRead]:
    """Get reviews for a product."""
    # Check if product exists
    product = await crud.get_product_by_id(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    reviews = await crud.get_reviews_by_product(db, product_id, skip=skip, limit=limit)
    return [schemas.ReviewRead.model_validate(r) for r in reviews]


# Cart endpoints (no auth required, but session_id needed)
@router.get("/cart", response_model=list[schemas.CartItemRead])
async def get_cart(
    db: Annotated[AsyncSession, Depends(get_db)],
    session_id: Optional[str] = Query(
        None, description="Session ID for anonymous cart"
    ),
    current_user: Optional[
        Annotated[user_schemas.UserRead, Depends(get_current_user)]
    ] = None,
) -> list[schemas.CartItemRead]:
    """Get cart items. Requires either authentication or session_id."""
    user_id = current_user.id if current_user else None
    if not user_id and not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either authentication or session_id is required",
        )
    cart_items = await crud.get_cart_items(db, user_id=user_id, session_id=session_id)
    return [schemas.CartItemRead.model_validate(item) for item in cart_items]


@router.post(
    "/cart", response_model=schemas.CartItemRead, status_code=status.HTTP_201_CREATED
)
async def add_to_cart(
    item_in: schemas.CartItemCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Optional[
        Annotated[user_schemas.UserRead, Depends(get_current_user)]
    ] = None,
) -> schemas.CartItemRead:
    """Add item to cart. Requires either authentication or session_id in request."""
    user_id = current_user.id if current_user else None
    session_id = item_in.session_id

    if not user_id and not session_id:
        # Generate session_id if not provided
        session_id = str(uuid4())

    cart_item = await crud.add_to_cart(
        db,
        product_id=item_in.product_id,
        quantity=item_in.quantity,
        user_id=user_id,
        session_id=session_id,
    )
    return schemas.CartItemRead.model_validate(cart_item)


@router.delete("/cart/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove item from cart."""
    await crud.remove_from_cart(db, item_id)


@router.delete("/cart", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    db: Annotated[AsyncSession, Depends(get_db)],
    session_id: Optional[str] = Query(
        None, description="Session ID for anonymous cart"
    ),
    current_user: Optional[
        Annotated[user_schemas.UserRead, Depends(get_current_user)]
    ] = None,
) -> None:
    """Clear cart. Requires either authentication or session_id."""
    user_id = current_user.id if current_user else None
    if not user_id and not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either authentication or session_id is required",
        )
    await crud.clear_cart(db, user_id=user_id, session_id=session_id)


# Order endpoints (require authentication)
@router.post(
    "/orders", response_model=schemas.OrderRead, status_code=status.HTTP_201_CREATED
)
async def create_order(
    order_in: schemas.OrderCreate,
    current_user: Annotated[user_schemas.UserRead, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.OrderRead:
    """Create order from cart. Requires authentication."""
    order = await crud.create_order_from_cart(
        db, user_id=current_user.id, session_id=order_in.session_id
    )
    return schemas.OrderRead.model_validate(order)


@router.get("/orders", response_model=list[schemas.OrderRead])
async def get_orders(
    current_user: Annotated[user_schemas.UserRead, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> list[schemas.OrderRead]:
    """Get user's orders. Requires authentication."""
    orders = await crud.get_user_orders(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return [schemas.OrderRead.model_validate(o) for o in orders]


@router.get("/orders/{order_id}", response_model=schemas.OrderRead)
async def get_order(
    order_id: int,
    current_user: Annotated[user_schemas.UserRead, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.OrderRead:
    """Get order details. Requires authentication."""
    order = await crud.get_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own orders",
        )
    return schemas.OrderRead.model_validate(order)


@router.post("/orders/{order_id}/pay", response_model=schemas.OrderRead)
async def pay_order(
    order_id: int,
    current_user: Annotated[user_schemas.UserRead, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.OrderRead:
    """Simulate payment for order. Requires authentication."""
    order = await crud.get_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only pay for your own orders",
        )
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order is already {order.status}",
        )

    # Simulate payment - generate fake payment_id
    payment_id = f"PAY_{order_id}_{uuid4().hex[:8].upper()}"
    order = await crud.update_order_status(db, order_id, "paid", payment_id=payment_id)
    return schemas.OrderRead.model_validate(order)


# Purchase endpoints (require authentication)
@router.get("/purchases", response_model=list[schemas.PurchaseRead])
async def get_purchases(
    current_user: Annotated[user_schemas.UserRead, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> list[schemas.PurchaseRead]:
    """Get user's purchase history. Requires authentication."""
    purchases = await crud.get_user_purchases(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return [schemas.PurchaseRead.model_validate(p) for p in purchases]


@router.get(
    "/purchases/{order_id}/content", response_model=list[schemas.PurchaseContentRead]
)
async def get_purchase_content(
    order_id: int,
    current_user: Annotated[user_schemas.UserRead, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[schemas.PurchaseContentRead]:
    """Get content text for purchased products. Requires authentication."""
    # Verify order belongs to user
    order = await crud.get_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access content from your own orders",
        )
    if order.status != "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be paid to access content",
        )

    content = await crud.get_purchase_content(
        db, user_id=current_user.id, order_id=order_id
    )
    return content


# Review endpoints (require authentication)
@router.post(
    "/products/{product_id}/reviews",
    response_model=schemas.ReviewRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    product_id: int,
    review_in: schemas.ReviewCreate,
    current_user: Annotated[user_schemas.UserRead, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.ReviewRead:
    """Create review for a product. Requires authentication and purchase."""
    # Check if product exists
    product = await crud.get_product_by_id(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    review = await crud.create_review(
        db, review_in=review_in, user_id=current_user.id, product_id=product_id
    )
    return schemas.ReviewRead.model_validate(review)


@router.put("/reviews/{review_id}", response_model=schemas.ReviewRead)
async def update_review(
    review_id: int,
    review_in: schemas.ReviewUpdate,
    current_user: Annotated[user_schemas.UserRead, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.ReviewRead:
    """Update own review. Requires authentication."""
    review = await crud.update_review(
        db, review_id=review_id, review_in=review_in, user_id=current_user.id
    )
    return schemas.ReviewRead.model_validate(review)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: int,
    current_user: Annotated[user_schemas.UserRead, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete own review. Requires authentication."""
    await crud.delete_review(db, review_id=review_id, user_id=current_user.id)
