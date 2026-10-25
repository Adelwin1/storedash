from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Order,
    OrderStatus,
)

from app.services.batch_db_adapter import (
    build_order_routing_input,
    get_driver_routing_context,
)

from app.services.batch_planner import (
    plan_batch_route,
)

from app.services.batch_route_pricing import (
    price_batch_plan,
)


PREVIEW_VERSION = (
    "storedash-manual-batch-preview-v1"
)


def preview_selected_batch(
    db: Session,
    *,
    driver_id: int,
    order_ids: list[int],
    driver_vehicle_id: int | None = None,
    duration_multiplier: float = 1.0,
    max_total_route_minutes: float | None = None,
) -> dict:

    if not order_ids:
        raise ValueError(
            "Select at least one order."
        )


    order_ids = list(
        dict.fromkeys(
            int(value)
            for value in order_ids
        )
    )


    if len(order_ids) > 12:
        raise ValueError(
            "A manual batch can contain "
            "at most 12 orders."
        )


    context = (
        get_driver_routing_context(
            db,

            driver_id=
                driver_id,

            driver_vehicle_id=
                driver_vehicle_id,
        )
    )


    orders = list(
        db.scalars(
            select(Order)
            .where(
                Order.id.in_(
                    order_ids
                )
            )
        ).all()
    )


    found = {
        order.id
        for order in orders
    }


    missing = [
        order_id
        for order_id in order_ids
        if order_id not in found
    ]


    if missing:
        raise ValueError(
            "Orders not found: "
            + ", ".join(
                str(value)
                for value in missing
            )
        )


    by_id = {
        order.id:
            order
        for order in orders
    }


    ordered_models = []

    inputs = []


    for order_id in order_ids:

        order = by_id[
            order_id
        ]


        if (
            order.status
            !=
            OrderStatus.READY_FOR_DISPATCH
        ):
            raise ValueError(
                f"Order {order.id} "
                "is not READY_FOR_DISPATCH."
            )


        if (
            order.assigned_driver_id
            is not None
        ):
            raise ValueError(
                f"Order {order.id} "
                "already has a driver."
            )


        built = (
            build_order_routing_input(
                db,
                order,
            )
        )


        ordered_models.append(
            order
        )


        inputs.append(
            built.input
        )


    plan = (
        plan_batch_route(
            orders=
                inputs,

            capacity=
                context.capacity,

            duration_multiplier=
                duration_multiplier,

            max_total_route_minutes=
                max_total_route_minutes,
        )
    )


    response = {
        "version":
            PREVIEW_VERSION,

        "driver_id":
            context.driver.id,

        "driver_name":
            context.driver.name,

        "driver_vehicle_id":
            context.vehicle.id,

        "vehicle":
            {
                "manufacturer":
                    context.spec.manufacturer,

                "model":
                    context.spec.model,

                "variant":
                    context.spec.variant,

                "registration":
                    context.vehicle.registration,
            },

        "capacity":
            context.capacity.to_dict(),

        "selected_order_ids":
            order_ids,

        "plan":
            asdict(
                plan
            ),

        "pricing":
            None,
    }


    if not plan.feasible:

        response[
            "message"
        ] = (
            "The selected orders do not "
            "fit this rider/vehicle route."
        )

        return response


    pricing = (
        price_batch_plan(
            context=
                context,

            plan=
                plan,

            orders=
                ordered_models,
        )
    )


    response[
        "pricing"
    ] = {
        "predicted_driver_payout":
            pricing.predicted_driver_payout,

        "predicted_contribution":
            pricing.predicted_contribution,

        "predicted_margin_rate":
            pricing.predicted_margin_rate,

        "policy_version":
            pricing.policy_version,

        "economics_version":
            pricing.economics_version,
    }


    response[
        "message"
    ] = (
        "Selected route is feasible."
    )


    return response
