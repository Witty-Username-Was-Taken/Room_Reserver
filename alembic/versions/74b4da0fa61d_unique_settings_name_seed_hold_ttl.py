"""unique settings name, seed hold_ttl

Revision ID: 74b4da0fa61d
Revises: 1a3cb381205b
Create Date: 2026-07-20 11:04:43.958933

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "74b4da0fa61d"
down_revision: Union[str, Sequence[str], None] = "1a3cb381205b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint("uq_settings_name", "settings", ["name"])
    op.execute("""
            INSERT INTO settings (name, value, comment)
               VALUES ('hold_ttl_minutes', '5', 'Lifetime of a pending hold before expiry')
               ON CONFLICT (name) DO NOTHING
               """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM settings WHERE name = 'hold_ttl_minutes'")
    op.drop_constraint("uq_settings_name", "settings")
