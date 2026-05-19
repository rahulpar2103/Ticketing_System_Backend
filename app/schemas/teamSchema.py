from pydantic import BaseModel, field_validator


class TeamCreate(BaseModel):
    name: str
    description: str

    @field_validator("name", "description", mode="before")
    @classmethod
    def strip_and_reject_empty(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Must be a string")
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v

    @field_validator("name")
    @classmethod
    def name_length(cls, v: str) -> str:
        if len(v) > 100:
            raise ValueError("Team name cannot exceed 100 characters")
        return v

    @field_validator("description")
    @classmethod
    def description_length(cls, v: str) -> str:
        if len(v) > 500:
            raise ValueError("Description cannot exceed 500 characters")
        return v

class TeamResponse(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool = True

    model_config = {
        "from_attributes": True
    }

class TeamUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def strip_and_reject_empty(cls, v: str) -> str:
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("Must be a string")
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v

    @field_validator("name")
    @classmethod
    def name_length(cls, v: str) -> str:
        if v is not None and len(v) > 100:
            raise ValueError("Team name cannot exceed 100 characters")
        return v

    @field_validator("description")
    @classmethod
    def description_length(cls, v: str) -> str:
        if v is not None and len(v) > 500:
            raise ValueError("Description cannot exceed 500 characters")
        return v

    model_config = {
        "from_attributes": True
    }
