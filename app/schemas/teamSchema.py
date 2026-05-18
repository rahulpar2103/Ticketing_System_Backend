from pydantic import BaseModel


class TeamCreate(BaseModel):
    name: str
    description: str

class TeamResponse(BaseModel):
    id: int
    name: str
    description: str

    model_config = {
        "from_attributes": True
    }

class TeamUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

    model_config = {
        "from_attributes": True
    }
