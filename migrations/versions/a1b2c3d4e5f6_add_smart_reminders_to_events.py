"""add smart reminders to events

Revision ID: a1b2c3d4e5f6
Revises: fb8164167767
Create Date: 2026-04-25 10:00:00.000000

Agrega las columnas necesarias para el sistema de recordatorios inteligentes:
- snooze_interval: intervalo en minutos entre recordatorios (default 10)
- reminder_active: si el usuario tiene los recordatorios activos
- next_reminder_at: cuándo enviar el próximo recordatorio
- reminder_count: contador de recordatorios enviados
- daily_reminder_sent_date: última fecha en que se envió recordatorio diario
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'fb8164167767'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('events', sa.Column('snooze_interval', sa.Integer(), nullable=True, server_default='10'))
    op.add_column('events', sa.Column('reminder_active', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('events', sa.Column('next_reminder_at', sa.DateTime(), nullable=True))
    op.add_column('events', sa.Column('reminder_count', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('events', sa.Column('daily_reminder_sent_date', sa.String(), nullable=True))

    # Índice para la consulta principal de recordatorios
    op.create_index('ix_events_next_reminder_at', 'events', ['next_reminder_at'], unique=False)
    op.create_index('ix_events_reminder_active', 'events', ['reminder_active'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_events_reminder_active', table_name='events')
    op.drop_index('ix_events_next_reminder_at', table_name='events')
    op.drop_column('events', 'daily_reminder_sent_date')
    op.drop_column('events', 'reminder_count')
    op.drop_column('events', 'next_reminder_at')
    op.drop_column('events', 'reminder_active')
    op.drop_column('events', 'snooze_interval')
