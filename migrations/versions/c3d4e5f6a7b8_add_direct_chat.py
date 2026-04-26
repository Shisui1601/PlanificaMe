"""add direct chat (contacts + messages)

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-25 12:00:00.000000

Crea dos tablas nuevas:
- direct_contacts: solicitudes de contacto entre usuarios (pending/accepted/declined)
- direct_messages: mensajes privados entre dos usuarios
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS direct_contacts (
            id VARCHAR PRIMARY KEY,
            requester_id VARCHAR REFERENCES users(id) ON DELETE CASCADE,
            receiver_id  VARCHAR REFERENCES users(id) ON DELETE CASCADE,
            status       VARCHAR DEFAULT 'pending',
            first_message TEXT,
            created_at   TIMESTAMP DEFAULT NOW(),
            updated_at   TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dc_requester ON direct_contacts(requester_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_dc_receiver  ON direct_contacts(receiver_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_dc_status    ON direct_contacts(status)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS direct_messages (
            id          VARCHAR PRIMARY KEY,
            sender_id   VARCHAR REFERENCES users(id) ON DELETE CASCADE,
            receiver_id VARCHAR REFERENCES users(id) ON DELETE CASCADE,
            content     TEXT NOT NULL,
            is_deleted  BOOLEAN DEFAULT FALSE,
            created_at  TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dm_sender   ON direct_messages(sender_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_dm_receiver ON direct_messages(receiver_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_dm_created  ON direct_messages(created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS direct_messages")
    op.execute("DROP TABLE IF EXISTS direct_contacts")
