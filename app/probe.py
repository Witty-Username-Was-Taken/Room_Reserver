import requests
import time
from datetime import datetime, timedelta, timezone


def get_current_time():
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    return now + timedelta(minutes=(15 - (now.minute % 15)))


def create_booking(start_time: datetime):
    url = "http://127.0.0.1:8000/bookings"

    payload = {
        "room_id": 1,
        "start_time": start_time.isoformat(),
        "end_time": (start_time + timedelta(minutes=15)).isoformat(),
    }

    response = requests.post(url, json=payload)

    return response


def invalid_times_booking(start_time: datetime):
    url = "http://127.0.0.1:8000/bookings"

    payload = {
        "room_id": 1,
        "start_time": (start_time + timedelta(minutes=15)).isoformat(),
        "end_time": start_time.isoformat(),
    }

    response = requests.post(url, json=payload)

    return response


def main():
    current_time = get_current_time()
    bad_times = invalid_times_booking(current_time)
    booking = create_booking(current_time)
    conflict = create_booking(current_time)

    # Expirations of booking test can be checked using UPDATE bookings SET expires_at = now() - interval '1 second' WHERE id = {returned_id}
    # TODO: implement DB connection to sent query and update

    assert bad_times.status_code == 422
    assert booking.status_code == 201
    assert conflict.status_code == 409


if __name__ == "__main__":
    main()
