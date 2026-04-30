"""add lineage, scenario registry, content-addressed artifacts, and governance fields

Revision ID: 20260430_0005
Revises: 20260425_0004
Create Date: 2026-04-30 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "20260430_0005"
down_revision = "20260425_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("run_artifacts", sa.Column("signature", sa.String(length=256), nullable=False, server_default=""))
    op.add_column(
        "run_artifacts",
        sa.Column("promotion_status", sa.String(length=32), nullable=False, server_default="draft"),
    )
    op.create_check_constraint(
        "ck_run_artifacts_promotion_status",
        "run_artifacts",
        "promotion_status IN ('draft', 'reviewed', 'approved', 'deprecated')",
    )
    op.alter_column("run_artifacts", "signature", server_default=None)
    op.alter_column("run_artifacts", "promotion_status", server_default=None)

    op.create_table(
        "scenario_registry",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("spread_multiplier", sa.Float(), nullable=False),
        sa.Column("latency_multiplier", sa.Float(), nullable=False),
        sa.Column("liquidity_haircut", sa.Float(), nullable=False),
        sa.Column("fee_change_bps", sa.Float(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("promotion_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("promotion_status IN ('draft', 'reviewed', 'approved', 'deprecated')", name="ck_scenario_registry_promotion_status"),
    )

    op.create_table(
        "artifact_blobs",
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("signature", sa.String(length=256), nullable=False),
        sa.Column("storage_uri", sa.String(length=1024), nullable=False),
        sa.Column("media_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("content_hash"),
    )

    op.create_table(
        "lineage_entities",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("immutable_ref", sa.String(length=256), nullable=False),
        sa.Column("artifact_hash", sa.String(length=128), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("promotion_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["artifact_hash"], ["artifact_blobs.content_hash"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_ref"),
        sa.CheckConstraint("promotion_status IN ('draft', 'reviewed', 'approved', 'deprecated')", name="ck_lineage_entities_promotion_status"),
    )

    op.create_table(
        "lineage_edges",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("source_entity_id", sa.String(length=128), nullable=False),
        sa.Column("target_entity_id", sa.String(length=128), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_entity_id"], ["lineage_entities.id"]),
        sa.ForeignKeyConstraint(["target_entity_id"], ["lineage_entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lineage_edges_source_entity_id", "lineage_edges", ["source_entity_id"])
    op.create_index("ix_lineage_edges_target_entity_id", "lineage_edges", ["target_entity_id"])

    op.create_table(
        "audit_reports",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("subject_entity_id", sa.String(length=128), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("validation_protocol", sa.JSON(), nullable=False),
        sa.Column("leakage_checks", sa.JSON(), nullable=False),
        sa.Column("sensitivity_outcomes", sa.JSON(), nullable=False),
        sa.Column("promotion_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["subject_entity_id"], ["lineage_entities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("promotion_status IN ('draft', 'reviewed', 'approved', 'deprecated')", name="ck_audit_reports_promotion_status"),
    )
    op.create_index("ix_audit_reports_subject_entity_id", "audit_reports", ["subject_entity_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_reports_subject_entity_id", table_name="audit_reports")
    op.drop_table("audit_reports")
    op.drop_index("ix_lineage_edges_target_entity_id", table_name="lineage_edges")
    op.drop_index("ix_lineage_edges_source_entity_id", table_name="lineage_edges")
    op.drop_table("lineage_edges")
    op.drop_table("lineage_entities")
    op.drop_table("artifact_blobs")
    op.drop_table("scenario_registry")
    op.drop_constraint("ck_run_artifacts_promotion_status", "run_artifacts", type_="check")
    op.drop_column("run_artifacts", "promotion_status")
    op.drop_column("run_artifacts", "signature")
