from pydantic import BaseModel
from datetime import datetime


class BusyInterval(BaseModel):
    start_time: datetime
    end_time: datetime


class RoomResponse(BaseModel):
    id: int
    building_id: int
    title: str | None
    room_num: str
    room_type: str
    capacity: int
