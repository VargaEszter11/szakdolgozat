import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from utils.nearest_airport import get_amadeus_token, AMADEUS_BASE_URL
from utils.coordinates import geocode_place

async def search_flight_offers(origin: str, destination: str, departure_date: str, return_date: Optional[str] = None):
    """Search for flight offers between two airports using Amadeus Flight Offers Search API."""
    access_token = await get_amadeus_token()
    
    url = f"{AMADEUS_BASE_URL}/v2/shopping/flight-offers"
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": departure_date,
        "adults": 1,
        "max": 5  # Get top 5 offers
    }
    
    if return_date:
        params["returnDate"] = return_date
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
    
    return data.get("data", [])

async def get_flight_price(offer_id: str):
    """Get confirmed price for a flight offer using Amadeus Flight Offers Price API."""
    access_token = await get_amadeus_token()
    
    url = f"{AMADEUS_BASE_URL}/v1/shopping/flight-offers/pricing"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Note: This requires the full offer object, not just ID
    # For now, we'll use a simplified approach
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json={"data": {"type": "flight-offer", "id": offer_id}}, headers=headers)
        response.raise_for_status()
        data = response.json()
    
    return data.get("data", {})

async def validate_plan_segment(origin_airport: str, dest_airport: str, date: str, budget: float) -> Dict[str, Any]:
    """Validate a single flight segment and get pricing information."""
    try:
        offers = await search_flight_offers(origin_airport, dest_airport, date)
        
        if not offers:
            return {
                "valid": False,
                "reason": "No flights available",
                "price": None
            }
        
        # Get the cheapest offer
        cheapest_offer = min(offers, key=lambda x: float(x.get("price", {}).get("total", "999999")))
        price = float(cheapest_offer.get("price", {}).get("total", 0))
        
        return {
            "valid": price <= budget,
            "price": price,
            "currency": cheapest_offer.get("price", {}).get("currency", "EUR"),
            "offer_id": cheapest_offer.get("id"),
            "reason": "Within budget" if price <= budget else f"Price {price} exceeds budget {budget}"
        }
    except Exception as e:
        return {
            "valid": False,
            "reason": f"Error validating flight: {str(e)}",
            "price": None
        }

async def validate_travel_plan(plan: Dict[str, Any], starting_airport: str, budget: int, travel_length: int) -> Dict[str, Any]:
    """Validate an entire travel plan by checking all flight segments and prices."""
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
    
    # Calculate dates (using current date + days)
    base_date = datetime.now() + timedelta(days=7)  # Start 7 days from now
    current_date = base_date
    total_price = 0
    validated_segments = []
    current_airport = starting_airport
    all_valid = True
    errors = []
    
    for i, segment in enumerate(segments):
        transport = segment.get("transportFromPreviousCity", "none")
        dest_city = segment.get("city", "")
        dest_country = segment.get("country", "")
        days = segment.get("days", 1)
        
        segment_validation = {
            "segment": segment,
            "validated": False,
            "price": 0,
            "error": None,
            "origin_airport": None,
            "destination_airport": None
        }
        
        if transport == "flight":
            # Get origin airport - use current_airport for first segment, otherwise look up from previous city
            origin_airport = current_airport
            if i > 0:
                # Get the previous city to find its airport
                prev_segment = segments[i - 1]
                prev_city = prev_segment.get("city", "")
                prev_country = prev_segment.get("country", "")
                prev_iata = prev_segment.get("iata")
                
                if prev_iata:
                    origin_airport = prev_iata
                elif prev_city:
                    # Look up airport for previous city using API
                    origin_airport = await get_city_airport_code(prev_city, prev_country)
                    if not origin_airport:
                        all_valid = False
                        segment_validation["error"] = f"Could not find airport for origin city {prev_city}, {prev_country}"
                        errors.append(segment_validation["error"])
                        current_date += timedelta(days=days)
                        validated_segments.append(segment_validation)
                        continue
            
            # Get destination airport - use IATA from plan if available, otherwise look it up
            dest_airport = segment.get("iata")
            
            if not dest_airport:
                # Look up airport code for destination city using API
                dest_airport = await get_city_airport_code(dest_city, dest_country)
            
            if not dest_airport:
                all_valid = False
                segment_validation["error"] = f"Could not find airport for destination city {dest_city}, {dest_country}"
                errors.append(segment_validation["error"])
            elif not origin_airport:
                all_valid = False
                segment_validation["error"] = f"Could not find origin airport"
                errors.append(segment_validation["error"])
            else:
                # Calculate departure date
                departure_date = current_date.strftime("%Y-%m-%d")
                
                # Validate flight segment using airport finder API for both origin and destination
                segment_result = await validate_plan_segment(
                    origin_airport, 
                    dest_airport, 
                    departure_date, 
                    budget - total_price  # Remaining budget
                )
                
                if segment_result["valid"]:
                    segment_validation["validated"] = True
                    segment_validation["price"] = segment_result["price"]
                    segment_validation["origin_airport"] = origin_airport
                    segment_validation["destination_airport"] = dest_airport
                    total_price += segment_result["price"]
                    current_airport = dest_airport
                else:
                    all_valid = False
                    segment_validation["error"] = segment_result["reason"]
                    errors.append(segment_result["reason"])
            
            current_date += timedelta(days=days)
        else:
            # For non-flight transport, estimate a small cost (e.g., train/bus)
            estimated_cost = 50 if transport in ["train", "bus"] else 0
            segment_validation["validated"] = True
            segment_validation["price"] = estimated_cost
            total_price += estimated_cost
            current_date += timedelta(days=days)
        
        validated_segments.append(segment_validation)
    
    # Calculate score: lower price and fewer errors = higher score
    # Score = (budget - total_price) / budget * 100, penalized by errors
    price_score = max(0, (budget - total_price) / budget * 100) if budget > 0 else 0
    error_penalty = len(errors) * 20
    final_score = max(0, price_score - error_penalty)
    
    # Calculate breakdown (only flights and transport)
    flight_cost = sum(s.get("price", 0) for s in validated_segments if s.get("validated") and s.get("segment", {}).get("transportFromPreviousCity") == "flight")
    transport_cost = sum(s.get("price", 0) for s in validated_segments if s.get("validated") and s.get("segment", {}).get("transportFromPreviousCity") != "flight")
    
    return {
        "valid": all_valid and total_price <= budget,
        "total_price": round(total_price, 2),
        "budget": budget,
        "remaining_budget": round(budget - total_price, 2),
        "cost_breakdown": {
            "flights": round(flight_cost, 2),
            "transport": round(transport_cost, 2)
        },
        "segments": validated_segments,
        "errors": errors,
        "score": round(final_score, 2),
        "reason": "Plan validated successfully" if all_valid and total_price <= budget else f"Validation failed: {', '.join(errors) if errors else f'Total price {total_price} exceeds budget {budget}'}"
    }

async def search_hotels_by_city(city_name: str, country_code: str, check_in: str, check_out: str) -> List[Dict[str, Any]]:
    """Search for hotels in a city using Amadeus Hotel Search API."""
    try:
        access_token = await get_amadeus_token()
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            # Get city coordinates for hotel search
            try:
                lat, lon = await geocode_place(f"{city_name}, {country_code}")
            except:
                # If geocoding fails, use estimated pricing
                return []
            
            # Use Hotel List API to find hotels by city
            url_list = f"{AMADEUS_BASE_URL}/v1/reference-data/locations/hotels/by-city"
            # Try to get city code - Amadeus uses IATA city codes
            # For now, we'll use a simplified approach with coordinates
            url_geo = f"{AMADEUS_BASE_URL}/v1/reference-data/locations/hotels/by-geocode"
            params_geo = {
                "latitude": lat,
                "longitude": lon,
                "radius": 5,
                "radiusUnit": "KM"
            }
            
            response = await client.get(url_geo, params=params_geo, headers=headers)
            if response.status_code == 200:
                hotel_data = response.json()
                hotel_ids = [hotel.get("hotelId") for hotel in hotel_data.get("data", [])[:5] if hotel.get("hotelId")]
                
                if hotel_ids:
                    # Search hotel offers
                    url_offers = f"{AMADEUS_BASE_URL}/v3/shopping/hotel-offers"
                    params_offers = {
                        "hotelIds": ",".join(hotel_ids),
                        "adults": 1,
                        "checkInDate": check_in,
                        "checkOutDate": check_out
                    }
                    
                    response_offers = await client.get(url_offers, params=params_offers, headers=headers)
                    if response_offers.status_code == 200:
                        offers_data = response_offers.json()
                        return offers_data.get("data", [])
        
        return []
    except Exception as e:
        print(f"Error searching hotels for {city_name}: {e}")
        return []

async def get_hotel_price(city_name: str, country_code: str, check_in: str, check_out: str, nights: int) -> Dict[str, Any]:
    """Get hotel price for a city and date range."""
    try:
        hotels = await search_hotels_by_city(city_name, country_code, check_in, check_out)
        
        if not hotels:
            # Estimate hotel cost if API doesn't return results
            estimated_price_per_night = 80  # Average European hotel price
            return {
                "valid": True,
                "price": estimated_price_per_night * nights,
                "price_per_night": estimated_price_per_night,
                "currency": "EUR",
                "source": "estimated"
            }
        
        # Get the cheapest hotel offer
        cheapest_price = None
        for hotel in hotels:
            offers = hotel.get("offers", [])
            for offer in offers:
                price = offer.get("price", {})
                total = float(price.get("total", "999999"))
                if cheapest_price is None or total < cheapest_price:
                    cheapest_price = total
        
        if cheapest_price:
            return {
                "valid": True,
                "price": cheapest_price * nights,
                "price_per_night": cheapest_price,
                "currency": "EUR",
                "source": "amadeus"
            }
        
        # Fallback to estimate
        estimated_price_per_night = 80
        return {
            "valid": True,
            "price": estimated_price_per_night * nights,
            "price_per_night": estimated_price_per_night,
            "currency": "EUR",
            "source": "estimated"
        }
    except Exception as e:
        # Fallback to estimate on error
        estimated_price_per_night = 80
        return {
            "valid": True,
            "price": estimated_price_per_night * nights,
            "price_per_night": estimated_price_per_night,
            "currency": "EUR",
            "source": "estimated",
            "error": str(e)
        }

async def search_activities_by_location(lat: float, lon: float, radius: int = 1) -> List[Dict[str, Any]]:
    """Search for activities near a location using Amadeus Activities API."""
    try:
        access_token = await get_amadeus_token()
        
        url = f"{AMADEUS_BASE_URL}/v1/shopping/activities"
        params = {
            "latitude": lat,
            "longitude": lon,
            "radius": radius
        }
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
        
        return data.get("data", [])
    except Exception as e:
        print(f"Error searching activities: {e}")
        return []

async def get_activity_price(city_name: str, country_code: str, days: int) -> Dict[str, Any]:
    """Get estimated activity/program costs for a city."""
    try:
        # Get city coordinates first (simplified - would need geocoding)
        # For now, estimate activity costs
        # Average activity cost per day in Europe: 30-50 EUR
        estimated_price_per_day = 40
        
        return {
            "valid": True,
            "price": estimated_price_per_day * days,
            "price_per_day": estimated_price_per_day,
            "currency": "EUR",
            "source": "estimated",
            "activities_count": days * 2  # Assume 2 activities per day
        }
    except Exception as e:
        estimated_price_per_day = 40
        return {
            "valid": True,
            "price": estimated_price_per_day * days,
            "price_per_day": estimated_price_per_day,
            "currency": "EUR",
            "source": "estimated",
            "error": str(e)
        }

async def get_city_airport_code(city_name: str, country_code: str = None) -> Optional[str]:
    """Get airport IATA code for a city using Amadeus Airport & City Search API."""
    try:
        access_token = await get_amadeus_token()
        
        url = f"{AMADEUS_BASE_URL}/v1/reference-data/locations"
        params = {
            "subType": "AIRPORT",
            "keyword": city_name,
            "max": 1
        }
        
        if country_code:
            params["countryCode"] = country_code
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
        
        airports = data.get("data", [])
        if airports:
            return airports[0].get("iataCode")
        
        return None
    except Exception as e:
        print(f"Error getting airport code for {city_name}: {e}")
        return None
