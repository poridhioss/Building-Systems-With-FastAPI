from sqlalchemy import Column, Integer, String, Boolean
from .database import Base


class User(Base):
    __tablename__ = "users"

    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True
    )

    # Email (used as username for login)
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    # Hashed password (NEVER store plain text!)
    hashed_password = Column(
        String(255),
        nullable=False
    )

    # Account status (allows soft-delete)
    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', is_active={self.is_active})>"