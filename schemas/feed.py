from pydantic import BaseModel

class ViewRequest(BaseModel):
    profile_id: int