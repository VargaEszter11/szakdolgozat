from typing import Dict, Any
from datetime import datetime, timedelta
from utils.flight_pricing import validate_plan_segment, get_city_airport_code
from utils.hotel_pricing import get_hotel_price
from utils.activity_pricing import get_activity_price
from utils.transport_pricing import estimate_ground_transport_cost


async def validate_travel_plan(plan: Dict[str, Any], starting_airport: str, budget: int, travel_length: int, start_date: str = None) -> Dict[str, Any]:
    """Validate an entire travel plan by checking all segments and prices."""
    if not plan or "plan" not in plan:
        return {
            "valid": False,
            "reason": "Invalid plan structure",
            "total_price": 0,
            "segments": [],
            "score": 0
        }

    segments = plan.get("plan", [])
    if not segments:
        return {
            "valid": False,
            "reason": "Plan has no segments",
            "total_price": 0,
            "segments": [],
            "score": 0
        }

    base_date = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.now() + timedelta(days=7)
    current_date = base_date
    total_price = 0
    validated_segments = []
    current_airport = starting_airport
    all_valid = True
    errors = []
    starting_point = plan.get("startingPoint", "")

    total_flight_cost = 0.0
    total_transport_cost = 0.0
    total_hotel_cost = 0.0
    total_activity_cost = 0.0

    for i, segment in enumerate(segments):
        transport = segment.get("transportFromPreviousCity", "none")
        dest_city = segment.get("city", "")
        dest_country = segment.get("country", "")
        days = segment.get("days", 1)

        segment_validation = {
            "segment": segment,
            "validated": False,
            "transport_price": 0,
            "hotel_price": 0,
            "activity_price": 0,
            "price": 0,
            "error": None,
            "origin_airport": None,
            "destination_airport": None
        }

        # --- Transport pricing ---
        if transport == "flight":
            origin_airport = current_airport
            if i > 0:
                prev_segment = segments[i - 1]
                prev_city = prev_segment.get("city", "")
                prev_country = prev_segment.get("country", "")
                prev_iata = prev_segment.get("iata")

                if prev_iata:
                    origin_airport = prev_iata
                elif prev_city:
                    origin_airport = await get_city_airport_code(prev_city, prev_country)
                    if not origin_airport:
                        all_valid = False
                        segment_validation["error"] = f"Could not find airport for origin city {prev_city}, {prev_country}"
                        errors.append(segment_validation["error"])
                        current_date += timedelta(days=days)
                        validated_segments.append(segment_validation)
                        continue

            dest_airport = segment.get("iata")
            if not dest_airport:
                dest_airport = await get_city_airport_code(dest_city, dest_country)

            if not dest_airport:
                all_valid = False
                segment_validation["error"] = f"Could not find airport for destination city {dest_city}, {dest_country}"
                errors.append(segment_validation["error"])
            elif not origin_airport:
                all_valid = False
                segment_validation["error"] = "Could not find origin airport"
                errors.append(segment_validation["error"])
            else:
                departure_date = current_date.strftime("%Y-%m-%d")
                segment_result = await validate_plan_segment(
                    origin_airport, dest_airport, departure_date,
                    budget - total_price
                )

                if segment_result["valid"]:
                    segment_validation["validated"] = True
                    segment_validation["transport_price"] = segment_result["price"]
                    segment_validation["origin_airport"] = origin_airport
                    segment_validation["destination_airport"] = dest_airport
                    total_flight_cost += segment_result["price"]
                    current_airport = dest_airport
                else:
                    all_valid = False
                    segment_validation["error"] = segment_result["reason"]
                    errors.append(segment_result["reason"])

        elif transport in ("train", "bus", "ferry"):
            origin_city = segments[i - 1].get("city", "") if i > 0 else starting_point
            cost = await estimate_ground_transport_cost(origin_city, dest_city, transport)
            segment_validation["validated"] = True
            segment_validation["transport_price"] = cost
            total_transport_cost += cost
        else:
            segment_validation["validated"] = True

        # --- Hotel pricing (for every segment) ---
        check_in = current_date.strftime("%Y-%m-%d")
        check_out = (current_date + timedelta(days=days)).strftime("%Y-%m-%d")
        hotel_result = await get_hotel_price(dest_city, dest_country, check_in, check_out, days)
        segment_validation["hotel_price"] = hotel_result.get("price", 0)
        total_hotel_cost += segment_validation["hotel_price"]

        # --- Activity pricing (for every segment) ---
        activity_result = await get_activity_price(dest_city, dest_country, days)
        segment_validation["activity_price"] = activity_result.get("price", 0)
        total_activity_cost += segment_validation["activity_price"]

        # --- Total segment price ---
        segment_validation["price"] = round(
            segment_validation["transport_price"]
            + segment_validation["hotel_price"]
            + segment_validation["activity_price"], 2
        )
        total_price = round(total_flight_cost + total_transport_cost + total_hotel_cost + total_activity_cost, 2)

        current_date += timedelta(days=days)
        validated_segments.append(segment_validation)

    price_score = max(0, (budget - total_price) / budget * 100) if budget > 0 else 0
    error_penalty = len(errors) * 20
    final_score = max(0, price_score - error_penalty)

    return {
        "valid": all_valid and total_price <= budget,
        "total_price": round(total_price, 2),
        "budget": budget,
        "remaining_budget": round(budget - total_price, 2),
        "cost_breakdown": {
            "flights": round(total_flight_cost, 2),
            "transport": round(total_transport_cost, 2),
            "hotels": round(total_hotel_cost, 2),
            "activities": round(total_activity_cost, 2),
        },
        "segments": validated_segments,
        "errors": errors,
        "score": round(final_score, 2),
        "reason": "Plan validated successfully" if all_valid and total_price <= budget else f"Validation failed: {', '.join(errors) if errors else f'Total price {total_price} exceeds budget {budget}'}"
    }
