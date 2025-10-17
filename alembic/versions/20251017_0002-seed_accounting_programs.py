"""Seed accounting programs for Hong Kong market

Revision ID: 20251017_0002
Revises: 20251017_0001
Create Date: 2025-10-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision: str = '20251017_0002'
down_revision: Union[str, None] = '20251017_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed accounting programs for Hong Kong."""

    # Define table for bulk insert
    accounting_programs = table(
        'accounting_programs',
        column('name', sa.String),
        column('jurisdiction', sa.String),
        column('vendor', sa.String),
        column('is_cloud_based', sa.Boolean),
        column('data_export_formats', sa.ARRAY(sa.String)),
    )

    # Hong Kong accounting software
    hk_programs = [
        {
            'name': 'Xero',
            'jurisdiction': 'HK',
            'vendor': 'Xero Limited',
            'is_cloud_based': True,
            'data_export_formats': ['CSV', 'PDF', 'Excel'],
        },
        {
            'name': 'QuickBooks Online',
            'jurisdiction': 'HK',
            'vendor': 'Intuit Inc.',
            'is_cloud_based': True,
            'data_export_formats': ['CSV', 'Excel', 'PDF'],
        },
        {
            'name': 'MYOB',
            'jurisdiction': 'HK',
            'vendor': 'MYOB Technology Pty Ltd',
            'is_cloud_based': True,
            'data_export_formats': ['CSV', 'Excel', 'PDF', 'XML'],
        },
        {
            'name': 'Sage 50',
            'jurisdiction': 'HK',
            'vendor': 'The Sage Group plc',
            'is_cloud_based': False,
            'data_export_formats': ['CSV', 'Excel', 'PDF'],
        },
        {
            'name': 'SAP Business One',
            'jurisdiction': 'HK',
            'vendor': 'SAP SE',
            'is_cloud_based': False,
            'data_export_formats': ['CSV', 'Excel', 'XML', 'PDF'],
        },
        {
            'name': 'Oracle NetSuite',
            'jurisdiction': 'HK',
            'vendor': 'Oracle Corporation',
            'is_cloud_based': True,
            'data_export_formats': ['CSV', 'Excel', 'PDF', 'XML'],
        },
        {
            'name': 'Zoho Books',
            'jurisdiction': 'HK',
            'vendor': 'Zoho Corporation',
            'is_cloud_based': True,
            'data_export_formats': ['CSV', 'Excel', 'PDF'],
        },
        {
            'name': 'FreshBooks',
            'jurisdiction': 'HK',
            'vendor': 'FreshBooks',
            'is_cloud_based': True,
            'data_export_formats': ['CSV', 'Excel', 'PDF'],
        },
        {
            'name': 'Wave',
            'jurisdiction': 'HK',
            'vendor': 'Wave Financial Inc.',
            'is_cloud_based': True,
            'data_export_formats': ['CSV', 'PDF'],
        },
        {
            'name': 'KashFlow',
            'jurisdiction': 'HK',
            'vendor': 'Iris Software Group',
            'is_cloud_based': True,
            'data_export_formats': ['CSV', 'Excel', 'PDF'],
        },
        {
            'name': 'Flexsystem',
            'jurisdiction': 'HK',
            'vendor': 'Flex System Holdings Limited',
            'is_cloud_based': False,
            'data_export_formats': ['CSV', 'Excel', 'PDF'],
        },
        {
            'name': 'ACCPAC',
            'jurisdiction': 'HK',
            'vendor': 'Sage Software',
            'is_cloud_based': False,
            'data_export_formats': ['CSV', 'Excel', 'PDF', 'XML'],
        },
        {
            'name': 'Microsoft Dynamics 365',
            'jurisdiction': 'HK',
            'vendor': 'Microsoft Corporation',
            'is_cloud_based': True,
            'data_export_formats': ['CSV', 'Excel', 'PDF', 'XML'],
        },
    ]

    # Insert data
    op.bulk_insert(accounting_programs, hk_programs)


def downgrade() -> None:
    """Remove seeded accounting programs."""
    op.execute("DELETE FROM accounting_programs WHERE jurisdiction = 'HK'")
