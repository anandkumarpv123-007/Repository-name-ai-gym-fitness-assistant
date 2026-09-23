import json
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.gym import Gym
from models.user import User
from models.profile import Profile
from schemas.planner import GymItemResponse, GymRecommendationItem, GymRecommendationResponse


DEFAULT_GYM_SAMPLES = [
    {
        "name": "Iron Forge Powerlifting & Heavy Lifting Club",
        "address": "104 Heavy Iron Way, Downtown",
        "city": "Metro City",
        "price_category": "mid_tier",
        "rating": 4.8,
        "opening_hours": "05:00 AM - 11:00 PM",
        "facilities": ["Squat Racks", "Deadlift Platforms", "Chalk Allowed", "Locker Room", "Free Parking"],
        "equipment": ["Barbells", "Dumbbells (up to 60kg)", "Bumper Plates", "Power Racks", "Cable Crossover", "Calf Raise Machine"],
        "supported_workout_types": ["hypertrophy", "strength", "powerlifting"],
        "is_verified_sample": True,
    },
    {
        "name": "Pulse HIIT & Endurance Fitness Studio",
        "address": "55 Aerobic Blvd, Westside",
        "city": "Metro City",
        "price_category": "budget",
        "rating": 4.6,
        "opening_hours": "06:00 AM - 10:00 PM",
        "facilities": ["Turf Zone", "Shower Rooms", "Air Conditioned", "Juice Bar"],
        "equipment": ["Assault Bikes", "Rowing Machines", "Kettlebells", "Plyo Boxes", "Treadmills", "Resistance Bands"],
        "supported_workout_types": ["weight_loss", "endurance", "hiit", "cardio"],
        "is_verified_sample": True,
    },
    {
        "name": "Metro Fitness & Wellness Complex",
        "address": "800 Central Avenue, Midtown",
        "city": "Metro City",
        "price_category": "premium",
        "rating": 4.9,
        "opening_hours": "05:30 AM - 11:30 PM",
        "facilities": ["Sauna", "Swimming Pool", "Steam Room", "Personal Training", "Locker Room", "Smoothie Bar"],
        "equipment": ["Squat Racks", "Dumbbells", "Treadmills", "Leg Press", "Lat Pulldown", "Smith Machine", "Ellipticals"],
        "supported_workout_types": ["hypertrophy", "maintenance", "weight_loss", "strength"],
        "is_verified_sample": True,
    },
    {
        "name": "Titan Athletics Bodybuilding Gym",
        "address": "42 Muscle Row, Industrial Zone",
        "city": "Metro City",
        "price_category": "budget",
        "rating": 4.7,
        "opening_hours": "Open 24/7",
        "facilities": ["Heavy Dumbbell Rack", "Pose Room", "Open 24/7", "Supplement Shop"],
        "equipment": ["Barbells", "Dumbbells (up to 70kg)", "Plate-Loaded Machines", "Hack Squat", "Preacher Curl Bench", "Cable Crossover"],
        "supported_workout_types": ["hypertrophy", "bodybuilding", "strength"],
        "is_verified_sample": True,
    },
    {
        "name": "Apex Functional Athletic Center",
        "address": "120 Sport Complex Road, North End",
        "city": "Metro City",
        "price_category": "mid_tier",
        "rating": 4.5,
        "opening_hours": "06:00 AM - 09:30 PM",
        "facilities": ["Olympic Lifting Platforms", "Rings & Rig Zone", "Recovery Ice Baths", "Locker Room"],
        "equipment": ["Olympic Barbells", "Kettlebells", "Pull-up Rigs", "Sleds & Turf", "Medicine Balls", "Rowing Machines"],
        "supported_workout_types": ["endurance", "strength", "functional_training", "weight_loss"],
        "is_verified_sample": True,
    },
    {
        "name": "Zenith Community Fitness Center",
        "address": "33 Parkview Lane, Suburbs",
        "city": "Metro City",
        "price_category": "budget",
        "rating": 4.2,
        "opening_hours": "07:00 AM - 09:00 PM",
        "facilities": ["Free Parking", "Senior Classes", "Locker Room"],
        "equipment": ["Selectorized Machines", "Treadmills", "Stationary Bikes", "Light Dumbbells", "Stretching Mats"],
        "supported_workout_types": ["maintenance", "general_fitness"],
        "is_verified_sample": True,
    },
    {
        "name": "Equinox Elite Athletic Club",
        "address": "1 Financial Plaza, Uptown",
        "city": "Metro City",
        "price_category": "premium",
        "rating": 4.9,
        "opening_hours": "05:00 AM - 11:00 PM",
        "facilities": ["Luxury Spa", "Steam Room", "Towel Service", "Private Lockers", "Roof Pool"],
        "equipment": ["Hammer Strength Machines", "Power Racks", "Woodway Treadmills", "Pilates Reformers", "Dumbbells"],
        "supported_workout_types": ["hypertrophy", "strength", "maintenance", "weight_loss"],
        "is_verified_sample": True,
    },
    {
        "name": "Vanguard Speed & Conditioning Lab",
        "address": "77 Performance Way, East District",
        "city": "Metro City",
        "price_category": "mid_tier",
        "rating": 4.6,
        "opening_hours": "06:00 AM - 10:00 PM",
        "facilities": ["Sprint Track", "Heart Rate Telemetry", "Cryotherapy", "Showers"],
        "equipment": ["Curved Treadmills", "SkiErgs", "Trap Bars", "Plyo Hurdles", "Kettlebells"],
        "supported_workout_types": ["endurance", "weight_loss", "athletic_conditioning"],
        "is_verified_sample": True,
    },
]


class GymRecommenderService:
    """
    Gym Catalogue & Recommendation Engine Service for Phase 7.
    Evaluates gym facilities, equipment, price tiers, and supported workout types
    against authenticated user context to calculate transparent suitability scores [0, 100%].
    """

    @classmethod
    def seed_default_gyms(cls, db: Session):
        """Seeds default synthetic gym catalogue entries if table is empty."""
        count = db.execute(select(Gym)).scalars().all()
        if len(count) > 0:
            return

        for item in DEFAULT_GYM_SAMPLES:
            gym = Gym(
                name=item["name"],
                address=item["address"],
                city=item["city"],
                price_category=item["price_category"],
                rating=item["rating"],
                opening_hours=item["opening_hours"],
                facilities_json=json.dumps(item["facilities"]),
                equipment_json=json.dumps(item["equipment"]),
                supported_workout_types_json=json.dumps(item["supported_workout_types"]),
                is_verified_sample=item["is_verified_sample"],
            )
            db.add(gym)
        db.commit()

    @classmethod
    def get_all_gyms(cls, db: Session, search: Optional[str] = None) -> List[GymItemResponse]:
        """Retrieves gym catalogue items, supporting keyword filtering."""
        cls.seed_default_gyms(db)

        query = select(Gym).order_by(Gym.rating.desc())
        gyms = db.execute(query).scalars().all()

        if search:
            search_lower = search.lower()
            gyms = [
                g for g in gyms
                if search_lower in g.name.lower()
                or search_lower in g.address.lower()
                or search_lower in g.price_category.lower()
                or search_lower in g.equipment_json.lower()
                or search_lower in g.facilities_json.lower()
            ]

        return [cls._to_gym_response(g) for g in gyms]

    @classmethod
    def recommend_gyms_for_user(cls, db: Session, user_id: int, limit: int = 5) -> GymRecommendationResponse:
        """
        Generates personalized ranked gym recommendations for specified user.
        Calculates a suitability score [0, 100%] based on goal matching, equipment compatibility,
        price tier, and facility amenities.
        """
        cls.seed_default_gyms(db)

        user = db.execute(select(User).where(User.id == user_id)).scalars().first()
        profile = user.profile if user else None
        fitness_goal = (profile.fitness_goal.lower() if profile and profile.fitness_goal else "maintenance")

        all_gyms = db.execute(select(Gym)).scalars().all()
        recommendation_items = []

        for gym in all_gyms:
            score, reasons = cls._calculate_suitability(gym, fitness_goal, profile)
            gym_resp = cls._to_gym_response(gym)

            if score >= 80:
                match_cat = "High Suitability Match"
            elif score >= 60:
                match_cat = "Moderate Suitability Match"
            else:
                match_cat = "Compatible Match"

            recommendation_items.append(
                GymRecommendationItem(
                    gym=gym_resp,
                    suitability_score=score,
                    match_category=match_cat,
                    match_reasons=reasons,
                )
            )

        # Sort recommendations by suitability_score descending, then rating descending
        recommendation_items.sort(key=lambda x: (x.suitability_score, x.gym.rating), reverse=True)

        return GymRecommendationResponse(
            user_id=user_id,
            user_goal=fitness_goal,
            recommendations=recommendation_items[:limit],
        )

    @classmethod
    def _calculate_suitability(cls, gym: Gym, goal: str, profile: Optional[Profile]) -> (int, List[str]):
        """
        Calculates transparent numerical suitability score [0, 100%] and match explanations.
        """
        score = 0
        reasons = []

        workout_types = json.loads(gym.supported_workout_types_json)
        equipment = json.loads(gym.equipment_json)
        facilities = json.loads(gym.facilities_json)

        # 1. Goal Compatibility (Max 45 pts)
        if goal in workout_types:
            score += 45
            reasons.append(f"Supports your target '{goal.replace('_', ' ').title()}' training goal.")
        elif any(g in workout_types for g in ["strength", "hypertrophy"]) and goal in ["hypertrophy", "strength"]:
            score += 35
            reasons.append(f"Equipped with strength & resistance infrastructure aligned with {goal.title()}.")
        elif any(g in workout_types for g in ["weight_loss", "endurance"]) and goal in ["weight_loss", "endurance"]:
            score += 35
            reasons.append(f"Offers cardio & conditioning equipment suited for {goal.title()}.")
        else:
            score += 20
            reasons.append("Provides general fitness equipment for active maintenance.")

        # 2. Equipment Compatibility (Max 30 pts)
        has_barbell = any("barbell" in e.lower() or "power rack" in e.lower() for e in equipment)
        has_dumbbells = any("dumbbell" in e.lower() for e in equipment)
        has_cardio = any("treadmill" in e.lower() or "bike" in e.lower() or "rowing" in e.lower() for e in equipment)

        if goal in ["hypertrophy", "strength"]:
            if has_barbell and has_dumbbells:
                score += 30
                reasons.append("Equipped with heavy barbells, power racks & dumbbell racks.")
            elif has_barbell or has_dumbbells:
                score += 20
                reasons.append("Contains resistance equipment suitable for progressive overload.")
        elif goal in ["weight_loss", "endurance"]:
            if has_cardio:
                score += 30
                reasons.append("Features extensive cardio equipment (Assault bikes, rowers, treadmills).")
            else:
                score += 15
                reasons.append("Offers basic conditioning tools.")
        else:
            score += 25
            reasons.append("Well-rounded mix of free weights and cardio machines.")

        # 3. Rating & Facility Quality (Max 25 pts)
        rating_pts = int(gym.rating * 4)  # 5.0 -> 20 pts
        score += rating_pts
        if gym.rating >= 4.7:
            reasons.append(f"Highly rated facility ({gym.rating:.1f}/5.0 stars) with premium member feedback.")
        else:
            reasons.append(f"Rated {gym.rating:.1f}/5.0 stars by local gym members.")

        if "Sauna" in facilities or "Recovery Ice Baths" in facilities or "Olympic Lifting Platforms" in facilities:
            score += 5
            reasons.append("Includes specialized recovery or performance amenities.")

        final_score = min(100, max(10, score))
        return final_score, reasons

    @classmethod
    def _to_gym_response(cls, gym: Gym) -> GymItemResponse:
        """Helper to convert Gym ORM model to Pydantic schema."""
        return GymItemResponse(
            id=gym.id,
            name=gym.name,
            address=gym.address,
            city=gym.city,
            price_category=gym.price_category,
            rating=gym.rating,
            opening_hours=gym.opening_hours,
            facilities=json.loads(gym.facilities_json),
            equipment=json.loads(gym.equipment_json),
            supported_workout_types=json.loads(gym.supported_workout_types_json),
            is_verified_sample=gym.is_verified_sample,
            created_at=gym.created_at,
        )
