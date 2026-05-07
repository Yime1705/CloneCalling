import re
from pydantic import BaseModel, Field, EmailStr, field_validator

class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)

    @field_validator("password")
    @classmethod
    def password_requires_special_char(cls, v):
        if not re.search(r"[!@#$%^&*()\-_=+\[\]{};:'\",.<>?/\\|`~]", v):
            raise ValueError("Password must contain at least one special character.")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=50)

class DailyBriefing(BaseModel):
    text: str = Field(..., min_length=5, max_length=1000)
    allowed_caller: EmailStr
