from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.profile import Profile


class User(Base):
    __tablename__ = "users"

    # Core authentication & account fields
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # 1-to-1 Relationship: User has one Profile
    profile: Mapped["Profile | None"] = relationship(
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # --- Backward-Compatibility Delegation to self.profile ---
    # These properties safely delegate to self.profile so existing untouched APIs
    # (e.g. GET /auth/me in Step 2B) continue functioning without error before Step 2C.
    @property
    def date_of_birth(self):
        return self.profile.date_of_birth if self.profile else None

    @date_of_birth.setter
    def date_of_birth(self, value):
        if self.profile:
            self.profile.date_of_birth = value

    @property
    def gender(self):
        return self.profile.gender if self.profile else None

    @gender.setter
    def gender(self, value):
        if self.profile:
            self.profile.gender = value

    @property
    def height_cm(self):
        return self.profile.height_cm if self.profile else None

    @height_cm.setter
    def height_cm(self, value):
        if self.profile:
            self.profile.height_cm = value

    @property
    def weight_kg(self):
        return self.profile.weight_kg if self.profile else None

    @weight_kg.setter
    def weight_kg(self, value):
        if self.profile:
            self.profile.weight_kg = value

    @property
    def fitness_goal(self):
        return self.profile.fitness_goal if self.profile else None

    @fitness_goal.setter
    def fitness_goal(self, value):
        if self.profile:
            self.profile.fitness_goal = value

    @property
    def activity_level(self):
        return self.profile.activity_level if self.profile else None

    @activity_level.setter
    def activity_level(self, value):
        if self.profile:
            self.profile.activity_level = value

    @property
    def dietary_preference(self):
        return self.profile.dietary_preference if self.profile else None

    @dietary_preference.setter
    def dietary_preference(self, value):
        if self.profile:
            self.profile.dietary_preference = value