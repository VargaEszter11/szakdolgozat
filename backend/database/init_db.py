"""
Database initialization script

This script creates all database tables and optionally seeds initial data.
Run this script once to set up the database schema.

Usage:
    python init_db.py
"""

import sys
from .database import engine, Base, SessionLocal
from . import models, crud, schemas
from datetime import date

def init_database():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("[SUCCESS] Database tables created successfully!")


def seed_sample_data():
    """Optionally seed the database with sample data"""
    db = SessionLocal()
    
    try:
        # Check if any users exist
        existing_users = db.query(models.User).first()
        if existing_users:
            print("Database already contains data. Skipping seed.")
            return
        
        print("\nSeeding sample data...")
        
        # Create a sample user
        sample_user = schemas.UserCreate(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        user = crud.create_user(db, sample_user)
        print(f"[SUCCESS] Created sample user: {user.username}")
        
        # Create a sample visited place
        sample_place = schemas.VisitedPlaceCreate(
            user_id=user.id,
            place_name="Budapest",
            country="Hungary",
            date=date(2022, 10, 3),
            rating=5,
            description="Capital of Hungary, rich in thermal baths and historical landmarks."
        )
        place = crud.create_visited_place(db, sample_place)
        print(f"[SUCCESS] Created sample visited place: {place.place_name}")
        
        # Create a sample planned trip
        sample_trip = schemas.PlannedTripCreate(
            user_id=user.id,
            title="European Adventure",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 15),
            start_city="Vienna"
        )
        trip = crud.create_planned_trip(db, sample_trip)
        print(f"[SUCCESS] Created sample planned trip: {trip.title}")
        
        # Create sample trip stops
        stops_data = [
            {
                "trip_id": trip.id,
                "place_name": "Prague",
                "country": "Czech Republic",
                "stop_order": 1,
                "arrival_date": date(2024, 6, 3),
                "departure_date": date(2024, 6, 6),
                "transport_from_last": "Train",
                "activities": "Visit Old Town, Charles Bridge",
                "estimated_price": 300.00
            },
            {
                "trip_id": trip.id,
                "place_name": "Krakow",
                "country": "Poland",
                "stop_order": 2,
                "arrival_date": date(2024, 6, 7),
                "departure_date": date(2024, 6, 10),
                "transport_from_last": "Bus",
                "activities": "Wawel Castle, Main Market Square",
                "estimated_price": 250.00
            }
        ]
        
        for stop_data in stops_data:
            stop = crud.create_trip_stop(db, schemas.TripStopCreate(**stop_data))
            print(f"[SUCCESS] Created trip stop: {stop.place_name}")
        
        print("\n[SUCCESS] Sample data seeded successfully!")
        
    except Exception as e:
        print(f"[ERROR] Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """Main initialization function"""
    print("=" * 60)
    print("Database Initialization Script")
    print("=" * 60)
    
    try:
        # Initialize database tables
        init_database()
        
        # Ask if user wants to seed sample data
        response = input("\nDo you want to seed sample data? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            seed_sample_data()
        else:
            print("Skipping sample data seed.")
        
        print("\n" + "=" * 60)
        print("Database initialization complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
