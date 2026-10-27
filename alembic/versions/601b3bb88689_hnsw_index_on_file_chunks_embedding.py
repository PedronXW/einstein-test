"""hnsw index on file_chunks.embedding

Revision ID: 601b3bb88689
Revises: 59f444c4518a
Create Date: 2026-10-27 16:39:06.491891

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '601b3bb88689'
down_revision: Union[str, Sequence[str], None] = '59f444c4518a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_file_chunks_embedding_hnsw "
        "ON file_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_file_chunks_embedding_hnsw")
