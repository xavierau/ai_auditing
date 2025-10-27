"""add summary column to worksheet_analyses

Revision ID: 27fbc143e68c
Revises: 4ffccbe4da52
Create Date: 2025-10-25 21:16:42.531766

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27fbc143e68c'
down_revision: Union[str, None] = '4ffccbe4da52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add summary column to worksheet_analyses table to store LLM-generated worksheet summaries
    op.add_column(
        'worksheet_analyses',
        sa.Column('summary', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    # Remove summary column from worksheet_analyses table
    op.drop_column('worksheet_analyses', 'summary')
