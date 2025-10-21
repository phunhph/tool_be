from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List
from pydantic.generics import GenericModel

T = TypeVar("T")

class ListResponse(GenericModel, Generic[T]):
    data: List[T]
    total: int
    pageSize: int
    pageIndex: int
    
# Response kiểu detail
class DetailResponse(GenericModel, Generic[T]):
    status: bool
    data: Optional[T]

# Response kiểu create
class CreateResponse(BaseModel):
    message: str
    status: bool
    objectId: int  # đổi userId -> objectId chung cho mọi module

# Response kiểu delete
class DeleteResponse(BaseModel):
    message: str
    status: bool
    objectId: int

# Response kiểu update
class UpdateResponse(GenericModel, Generic[T]):
    message: str
    status: bool
    data: T
