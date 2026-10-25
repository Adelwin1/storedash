from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import BaseModel

from sqlalchemy import select

from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.core.db import get_db

from app.models import (
    Business,
    Order,
    OrderStatus,
)


router = APIRouter(
    prefix="/businesses",
    tags=["customer-insights"],
)


class FrequentProductRead(BaseModel):
    name: str
    purchase_count: int
    total_quantity: float
    average_quantity: float
    last_quantity: float
    unit: str
    last_purchase_at: datetime
    last_order_id: int
    last_order_number: str


class PurchaseSummaryRead(BaseModel):
    business_id: int
    completed_order_count: int
    unique_product_count: int
    frequent_products: list[
        FrequentProductRead
    ]


@router.get(
    "/{business_id}/purchase-summary",
    response_model=PurchaseSummaryRead,
)
def purchase_summary(
    business_id: int,
    db: Session = Depends(get_db),
):
    business = db.get(
        Business,
        business_id,
    )

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )


    orders = db.scalars(
        select(Order)
        .options(
            selectinload(
                Order.items
            )
        )
        .where(
            Order.business_id
            == business_id,

            Order.status
            == OrderStatus.COMPLETED,
        )
        .order_by(
            Order.created_at.asc()
        )
    ).unique().all()


    products: dict[
        str,
        dict,
    ] = {}


    for order in orders:
        purchase_time = (
            order.completed_at
            or order.created_at
        )

        for item in order.items:
            normalized_name = (
                item.name
                .strip()
                .casefold()
            )

            if not normalized_name:
                continue


            quantity = float(
                item.requested_quantity
                or 0
            )


            if normalized_name not in products:
                products[
                    normalized_name
                ] = {
                    "name":
                        item.name.strip(),

                    "purchase_count":
                        0,

                    "total_quantity":
                        0.0,

                    "last_quantity":
                        quantity,

                    "unit":
                        item.unit,

                    "last_purchase_at":
                        purchase_time,

                    "last_order_id":
                        order.id,

                    "last_order_number":
                        order.order_number,
                }


            product = products[
                normalized_name
            ]


            product[
                "purchase_count"
            ] += 1


            product[
                "total_quantity"
            ] += quantity


            if (
                purchase_time
                >= product[
                    "last_purchase_at"
                ]
            ):
                product[
                    "name"
                ] = item.name.strip()

                product[
                    "last_quantity"
                ] = quantity

                product[
                    "unit"
                ] = item.unit

                product[
                    "last_purchase_at"
                ] = purchase_time

                product[
                    "last_order_id"
                ] = order.id

                product[
                    "last_order_number"
                ] = order.order_number


    frequent_products = []


    for product in products.values():
        count = product[
            "purchase_count"
        ]

        total = product[
            "total_quantity"
        ]


        frequent_products.append(
            FrequentProductRead(
                name=product[
                    "name"
                ],

                purchase_count=count,

                total_quantity=round(
                    total,
                    2,
                ),

                average_quantity=round(
                    total / count,
                    2,
                ),

                last_quantity=round(
                    product[
                        "last_quantity"
                    ],
                    2,
                ),

                unit=product[
                    "unit"
                ],

                last_purchase_at=product[
                    "last_purchase_at"
                ],

                last_order_id=product[
                    "last_order_id"
                ],

                last_order_number=product[
                    "last_order_number"
                ],
            )
        )


    frequent_products.sort(
        key=lambda product: (
            product.purchase_count,
            product.last_purchase_at,
        ),
        reverse=True,
    )


    return PurchaseSummaryRead(
        business_id=business_id,

        completed_order_count=len(
            orders
        ),

        unique_product_count=len(
            frequent_products
        ),

        frequent_products=(
            frequent_products
        ),
    )
