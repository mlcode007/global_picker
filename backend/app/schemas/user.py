from pydantic import BaseModel


class UserLogin(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    is_active: int

    model_config = {"from_attributes": True}
