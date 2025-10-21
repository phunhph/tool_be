from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.db import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    login_id = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)  # liên kết role
    is_delete = Column(Boolean, default=False)

    role = relationship("Role")