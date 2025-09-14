from pydantic import BaseModel

class DocCreate(BaseModel):
        title: str | None = "Untitled Document"
        content: str | None = ""


class DocOut(BaseModel):
    id: str
    title: str
    content: str
    version: int


    class Config:
        orm_mode = True