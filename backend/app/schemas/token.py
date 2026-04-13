"""Schemas para respuestas JWT."""
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: str
    organization_id: str
    role: str
    email: str
