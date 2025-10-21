from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    role: str

    class Config:
        orm_mode = True
