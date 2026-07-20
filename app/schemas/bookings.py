from pydantic import BaseModel, model_validator, ConfigDict
from datetime import datetime
from app.models import BookingStatus


class BookingRequest(BaseModel):
    room_id: int
    start_time: datetime
    end_time: datetime

    # This will handle raise 422 errors.
    @model_validator(mode="after")
    def validate_times(self) -> "BookingRequest":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        for t in (self.start_time, self.end_time):
            if t.minute % 15 or t.second or t.microsecond:
                raise ValueError("times must align to 15 minute boundaries")
        return self


class BookingResponse(BaseModel):
    id: int
    room_id: int
    start_time: datetime
    end_time: datetime
    expires_at: datetime
    created_at: datetime
    status: BookingStatus
    model_config = ConfigDict(from_attributes=True)
