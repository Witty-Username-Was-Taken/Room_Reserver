import requests
import psycopg
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


def confirm_booking(booking_id: int):
    url = f"http://127.0.0.1:8000/bookings/{booking_id}/confirm"

    response = requests.post(url)

    return response


def update_booking_expiry(booking_id: int):
    with psycopg.connect("postgresql://booking:booking@localhost:5432/booking") as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE bookings SET expires_at = now() - interval '1 second' WHERE id = %s",
                (booking_id,),
            )
            assert cur.rowcount == 1, (
                f"expected to expire booking {booking_id}, touched {cur.rowcount} rows"
            )


def main():
    current_time = get_current_time()
    bad_times = invalid_times_booking(current_time)
    booking = create_booking(current_time)
    conflict = create_booking(current_time)

    assert bad_times.status_code == 422
    assert booking.status_code == 201
    assert conflict.status_code == 409

    booking_id = booking.json()["id"]

    update_booking_expiry(booking_id)

    expired_confirm = confirm_booking(booking_id)
    new_booking = create_booking(current_time)
    booking_id = new_booking.json()["id"]

    confirm = confirm_booking(booking_id)
    confirm_duplicate = confirm_booking(booking_id)

    assert expired_confirm.status_code == 410
    assert new_booking.status_code == 201
    assert confirm.status_code == 200
    assert confirm_duplicate.status_code == 200


if __name__ == "__main__":
    main()
