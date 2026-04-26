from pydantic import BaseModel, Field, EmailStr

class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=50)

class DailyBriefing(BaseModel):
    text: str = Field(..., min_length=5, max_length=1000)
    allowed_caller: EmailStr

class AudioRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)