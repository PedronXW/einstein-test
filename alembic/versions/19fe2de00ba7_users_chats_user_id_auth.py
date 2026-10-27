"""users + chats.user_id (auth)

Revision ID: 19fe2de00ba7
Revises: a1b52215eda6
Create Date: 2026-10-27 14:18:20.031155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "19fe2de00ba7"
down_revision: Union[str, Sequence[str], None] = "a1b52215eda6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_NAME = "fk_chats_user_id_users"
MIGRATION_USER_EMAIL = "sistema@einstein.test"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.add_column("chats", sa.Column("user_id", sa.Integer(), nullable=True))
    # Backfill: chats existentes (sem dono) passam para um usuário de migração,
    # preservando acesso num caminho de administração/bootstrap.
    op.execute(
        sa.text(
            "INSERT INTO users (email, password_hash) "
            f"VALUES ('{MIGRATION_USER_EMAIL}', '!') "
            "ON CONFLICT (email) DO NOTHING"
        )
    )
    op.execute(
        sa.text(
            "UPDATE chats SET user_id = "
            f"(SELECT id FROM users WHERE email = '{MIGRATION_USER_EMAIL}') "
            "WHERE user_id IS NULL"
        )
    )
    op.alter_column("chats", "user_id", nullable=False)
    op.create_index(op.f("ix_chats_user_id"), "chats", ["user_id"], unique=False)
    op.create_foreign_key(FK_NAME, "chats", "users", ["user_id"], ["id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(FK_NAME, "chats", type_="foreignkey")
    op.drop_index(op.f("ix_chats_user_id"), table_name="chats")
    op.drop_column("chats", "user_id")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")