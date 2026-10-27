"""user.model (modelo de análise selecionado)

Revision ID: c19610cbe5e6
Revises: 601b3bb88689
Create Date: 2026-10-27 19:21:56.862351

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c19610cbe5e6'
down_revision: Union[str, Sequence[str], None] = '601b3bb88689'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # nota: NÃO remover o índice HNSW (o autogenerate não detecta CREATE INDEX
    # raw do pgvector) — apenas adiciona a coluna users.model.
    op.add_column('users', sa.Column('model', sa.String(length=127), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'model')
