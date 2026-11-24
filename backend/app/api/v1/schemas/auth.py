import uuid

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    # Sem EmailStr: o login responde de forma genérica de qualquer jeito.
    email: str = Field(max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
