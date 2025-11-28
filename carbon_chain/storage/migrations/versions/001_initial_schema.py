"""
Initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-11-27 17:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create initial database schema for CarbonChain.
    """
    
    # ========================================================================
    # BLOCKS TABLE
    # ========================================================================
    
    op.create_table(
        'blocks',
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('hash', sa.LargeBinary(length=32), nullable=False),
        sa.Column('prev_hash', sa.LargeBinary(length=32), nullable=False),
        sa.Column('merkle_root', sa.LargeBinary(length=32), nullable=False),
        sa.Column('timestamp', sa.BigInteger(), nullable=False),
        sa.Column('difficulty', sa.Integer(), nullable=False),
        sa.Column('nonce', sa.BigInteger(), nullable=False),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('height')
    )
    
    # Indexes for blocks
    op.create_index('idx_blocks_hash', 'blocks', ['hash'], unique=True)
    op.create_index('idx_blocks_timestamp', 'blocks', ['timestamp'])
    
    # ========================================================================
    # TRANSACTIONS TABLE
    # ========================================================================
    
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('txid', sa.LargeBinary(length=32), nullable=False),
        sa.Column('block_height', sa.Integer(), nullable=True),
        sa.Column('tx_type', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.BigInteger(), nullable=False),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['block_height'], ['blocks.height']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for transactions
    op.create_index('idx_transactions_txid', 'transactions', ['txid'], unique=True)
    op.create_index('idx_transactions_block', 'transactions', ['block_height'])
    op.create_index('idx_transactions_type', 'transactions', ['tx_type'])
    op.create_index('idx_transactions_timestamp', 'transactions', ['timestamp'])
    
    # ========================================================================
    # UTXOS TABLE
    # ========================================================================
    
    op.create_table(
        'utxos',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('txid', sa.LargeBinary(length=32), nullable=False),
        sa.Column('output_index', sa.Integer(), nullable=False),
        sa.Column('amount', sa.BigInteger(), nullable=False),
        sa.Column('address', sa.String(length=256), nullable=False),
        sa.Column('coin_state', sa.String(length=50), nullable=False),
        sa.Column('certificate_id', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for UTXOs
    op.create_index('idx_utxos_address', 'utxos', ['address'])
    op.create_index('idx_utxos_certificate', 'utxos', ['certificate_id'])
    op.create_index('idx_utxos_state', 'utxos', ['coin_state'])
    op.create_index(
        'idx_utxos_composite',
        'utxos',
        ['txid', 'output_index'],
        unique=True
    )
    
    # ========================================================================
    # CERTIFICATES TABLE
    # ========================================================================
    
    op.create_table(
        'certificates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('certificate_id', sa.String(length=50), nullable=False),
        sa.Column('project_id', sa.String(length=50), nullable=False),
        sa.Column('vintage', sa.Integer(), nullable=False),
        sa.Column('total_amount', sa.BigInteger(), nullable=False),
        sa.Column('assigned_amount', sa.BigInteger(), nullable=False),
        sa.Column('compensated_amount', sa.BigInteger(), nullable=False),
        sa.Column('location', sa.String(length=256), nullable=True),
        sa.Column('certificate_type', sa.String(length=50), nullable=False),
        sa.Column('standard', sa.String(length=50), nullable=True),
        sa.Column('issue_date', sa.BigInteger(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for certificates
    op.create_index('idx_certificates_id', 'certificates', ['certificate_id'], unique=True)
    op.create_index('idx_certificates_project', 'certificates', ['project_id'])
    op.create_index('idx_certificates_type', 'certificates', ['certificate_type'])
    op.create_index('idx_certificates_vintage', 'certificates', ['vintage'])


def downgrade() -> None:
    """
    Drop all tables (reverse migration).
    """
    op.drop_table('certificates')
    op.drop_table('utxos')
    op.drop_table('transactions')
    op.drop_table('blocks')
