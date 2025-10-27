"""increase coding_system column size to text

Revision ID: 4ffccbe4da52
Revises: 836ed694a5af
Create Date: 2025-10-25 19:36:28.301831

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ffccbe4da52'
down_revision: Union[str, None] = '836ed694a5af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change coding_system from VARCHAR(255) to TEXT to support longer LLM-generated descriptions
    op.alter_column(
        'relationship_maps',
        'coding_system',
        type_=sa.Text(),
        existing_type=sa.String(255),
        existing_nullable=True
    )


def downgrade() -> None:
    # Revert coding_system from TEXT back to VARCHAR(255)
    op.alter_column(
        'relationship_maps',
        'coding_system',
        type_=sa.String(255),
        existing_type=sa.Text(),
        existing_nullable=True
    )
