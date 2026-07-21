import requests
import time
from datetime import datetime, timedelta


def get_current_time():
    now = datetime.now()
    current_minute = now.minute

    rounded_minute = 15 * round(current_minute / 15)

    if rounded_minute == 60:
        closest_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(
            hours=1
        )
    else:
        closest_time = now.replace(minute=rounded_minute, second=0, microsecond=0)

    return closest_time


def create_booking(start_time: datetime):
    url = "http://127.0.0.1:8000/bookings"

    payload = {
        "room_id": "1",
        "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": (start_time + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
    }

    response = requests.post(url, json=payload)

    return response


def invalid_times_booking(start_time: datetime):
    url = "http://127.0.0.1:8000/bookings"

    payload = {
        "room_id": "1",
        "start_time": (start_time + timedelta(minutes=15)).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "end_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    response = requests.post(url, json=payload)

    return response


def main():
    current_time = get_current_time()

    bad_times = invalid_times_booking(current_time)
    booking = create_booking(current_time)
    conflict = create_booking(current_time)
    time.sleep(301)  # Wait just a little over 5 minutes
    taking_expired = create_booking(current_time)

    print(f"Bad Times: {bad_times.json()}")
    print(f"Booking: {booking.json()}")
    print(f"Conflict: {conflict.json()}")
    print(f"Taking expired booking: {taking_expired.json()}")


if __name__ == "__main__":
    main()
