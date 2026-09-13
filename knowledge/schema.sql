PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL,
    title TEXT NOT NULL,
    section TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    kind TEXT NOT NULL,
    UNIQUE(path, section)
);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    path,
    title,
    section,
    content,
    content='documents',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(rowid, path, title, section, content)
    VALUES (new.id, new.path, new.title, new.section, new.content);
END;

CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, path, title, section, content)
    VALUES ('delete', old.id, old.path, old.title, old.section, old.content);
END;

CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, path, title, section, content)
    VALUES ('delete', old.id, old.path, old.title, old.section, old.content);
    INSERT INTO documents_fts(rowid, path, title, section, content)
    VALUES (new.id, new.path, new.title, new.section, new.content);
END;

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    kind TEXT NOT NULL,
    topics_json TEXT NOT NULL,
    license TEXT NOT NULL,
    use_text TEXT NOT NULL,
    authority TEXT NOT NULL,
    status TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    source_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS governance_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS governance_claims (
    claim_id TEXT PRIMARY KEY,
    branch_key TEXT NOT NULL,
    statement TEXT NOT NULL,
    authority_class TEXT NOT NULL,
    lifecycle TEXT NOT NULL,
    status TEXT NOT NULL,
    source_system TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    support_count INTEGER NOT NULL,
    independent_support_count INTEGER NOT NULL,
    verified_at TEXT NOT NULL,
    valid_through TEXT,
    supersedes_json TEXT NOT NULL,
    claim_hash TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS governance_claims_fts USING fts5(
    claim_id UNINDEXED,
    statement,
    branch_key,
    authority_class,
    lifecycle,
    status
);

CREATE TABLE IF NOT EXISTS branch_state (
    branch_key TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    branch_type TEXT NOT NULL,
    owner_agent TEXT NOT NULL,
    github_paths_json TEXT NOT NULL,
    dependencies_json TEXT NOT NULL,
    exclusions_json TEXT NOT NULL,
    retrieval_packet TEXT NOT NULL,
    upstream_ref TEXT NOT NULL,
    tracking_json TEXT NOT NULL,
    row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS system_feedback (
    event_id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    branch_key TEXT NOT NULL,
    category TEXT NOT NULL,
    signature TEXT NOT NULL,
    summary TEXT NOT NULL,
    evidence_ref TEXT NOT NULL,
    severity TEXT NOT NULL,
    disposition TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_roots (
    root_id TEXT PRIMARY KEY,
    root_kind TEXT NOT NULL,
    observation_question TEXT NOT NULL,
    input_identity TEXT NOT NULL DEFAULT '',
    execution_identity TEXT NOT NULL DEFAULT '',
    source_revision TEXT NOT NULL DEFAULT '',
    environment_identity TEXT NOT NULL DEFAULT '',
    provenance_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS atomic_findings (
    finding_id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    branch_key TEXT NOT NULL,
    claim_key TEXT NOT NULL,
    value_text TEXT NOT NULL,
    evidence_ref TEXT NOT NULL,
    root_ids_json TEXT NOT NULL,
    lineage_state TEXT NOT NULL,
    shared_input_keys_json TEXT NOT NULL,
    related_claim_keys_json TEXT NOT NULL,
    supersedes_claim_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS finding_assessments (
    assessment_id TEXT PRIMARY KEY,
    finding_id TEXT NOT NULL,
    cross_reference TEXT NOT NULL,
    current_claim_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(finding_id) REFERENCES atomic_findings(finding_id)
);

CREATE TABLE IF NOT EXISTS triangulation_batches (
    batch_id TEXT PRIMARY KEY,
    claim_key TEXT NOT NULL,
    state TEXT NOT NULL,
    root_summary_json TEXT NOT NULL,
    supporting_root_ids_json TEXT NOT NULL,
    contradicting_root_ids_json TEXT NOT NULL,
    notes_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_delta_packets (
    delta_id TEXT PRIMARY KEY,
    claim_key TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS improvement_candidates AS
SELECT
    branch_key,
    category,
    signature,
    COUNT(*) AS occurrence_count,
    COUNT(DISTINCT episode_id) AS independent_episode_count,
    MIN(created_at) AS first_seen,
    MAX(created_at) AS last_seen
FROM system_feedback
WHERE disposition = 'open'
GROUP BY branch_key, category, signature
HAVING COUNT(DISTINCT episode_id) >= 2;

CREATE INDEX IF NOT EXISTS idx_documents_path ON documents(path);
CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status);
CREATE INDEX IF NOT EXISTS idx_governance_branch ON governance_claims(branch_key);
CREATE INDEX IF NOT EXISTS idx_governance_authority ON governance_claims(authority_class);
CREATE INDEX IF NOT EXISTS idx_branch_state_status ON branch_state(status);
CREATE INDEX IF NOT EXISTS idx_feedback_signature ON system_feedback(signature);
CREATE INDEX IF NOT EXISTS idx_feedback_branch ON system_feedback(branch_key);
CREATE INDEX IF NOT EXISTS idx_findings_claim_key ON atomic_findings(claim_key);
CREATE INDEX IF NOT EXISTS idx_findings_episode ON atomic_findings(episode_id);
CREATE INDEX IF NOT EXISTS idx_tri_claim_key ON triangulation_batches(claim_key);
