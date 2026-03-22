from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('generation_jobs',
        sa.Column('job_payload', sa.JSON(), nullable=True)
    )

def downgrade():
    op.drop_column('generation_jobs', 'job_payload')
