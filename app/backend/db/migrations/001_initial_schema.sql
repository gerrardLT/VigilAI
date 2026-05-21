-- ============================================================================
-- VigilAI Initial Schema Migration
-- Extracted from: data_manager.py, agent_platform/repository.py,
--                 product_selection/repository.py, reward_opportunity/repository.py
-- Generated: 2025
-- ============================================================================

-- ============================================================================
-- Core Tables (from data_manager.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS activities (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    full_content TEXT,
    source_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    url TEXT NOT NULL,
    category TEXT NOT NULL,
    tags TEXT,
    prize_amount REAL,
    prize_currency TEXT,
    prize_description TEXT,
    start_date TEXT,
    end_date TEXT,
    deadline TEXT,
    location TEXT,
    organizer TEXT,
    image_url TEXT,
    summary TEXT,
    score REAL,
    score_reason TEXT,
    deadline_level TEXT,
    trust_level TEXT,
    updated_fields TEXT,
    analysis_fields TEXT,
    analysis_status TEXT,
    analysis_failed_layer TEXT,
    analysis_summary_reasons TEXT,
    analysis_summary TEXT,
    analysis_reasons TEXT,
    analysis_risk_flags TEXT,
    analysis_recommended_action TEXT,
    analysis_confidence REAL,
    analysis_structured TEXT,
    analysis_template_id TEXT,
    analysis_current_run_id TEXT,
    analysis_updated_at TEXT,
    status TEXT DEFAULT 'upcoming',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source_id, url)
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    url TEXT NOT NULL,
    priority TEXT NOT NULL,
    update_interval INTEGER NOT NULL,
    enabled INTEGER DEFAULT 1,
    last_run TEXT,
    last_success TEXT,
    status TEXT DEFAULT 'idle',
    error_message TEXT,
    activity_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tracking_items (
    activity_id TEXT PRIMARY KEY,
    is_favorited INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'saved',
    stage TEXT,
    notes TEXT,
    next_action TEXT,
    remind_at TEXT,
    block_reason TEXT,
    abandon_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS digests (
    id TEXT PRIMARY KEY,
    digest_date TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT NOT NULL,
    item_ids TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_sent_at TEXT,
    send_channel TEXT
);

CREATE TABLE IF NOT EXISTS digest_candidates (
    digest_date TEXT NOT NULL,
    activity_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (digest_date, activity_id)
);

CREATE TABLE IF NOT EXISTS analysis_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    is_default INTEGER DEFAULT 0,
    tags TEXT NOT NULL,
    layers TEXT NOT NULL,
    sort_fields TEXT NOT NULL,
    preference_profile TEXT,
    risk_tolerance TEXT,
    research_mode TEXT,
    compiled_policy TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- ============================================================================
-- Analysis Agent Tables (from data_manager.py _init_agent_analysis_tables)
-- ============================================================================

CREATE TABLE IF NOT EXISTS analysis_jobs (
    id TEXT PRIMARY KEY,
    trigger_type TEXT NOT NULL,
    scope_type TEXT NOT NULL,
    template_id TEXT,
    route_policy TEXT,
    budget_policy TEXT,
    status TEXT NOT NULL,
    requested_by TEXT,
    created_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS analysis_job_items (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    activity_id TEXT NOT NULL,
    status TEXT NOT NULL,
    needs_research INTEGER DEFAULT 0,
    final_draft_status TEXT,
    screening_model TEXT,
    research_model TEXT,
    verdict_model TEXT,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_item_steps (
    id TEXT PRIMARY KEY,
    job_item_id TEXT NOT NULL,
    step_type TEXT NOT NULL,
    step_status TEXT NOT NULL,
    input_digest TEXT,
    output_payload TEXT,
    latency_ms INTEGER,
    cost_tokens_in INTEGER,
    cost_tokens_out INTEGER,
    model_name TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_evidence (
    id TEXT PRIMARY KEY,
    job_item_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    url TEXT,
    title TEXT,
    snippet TEXT,
    relevance_score REAL,
    trust_score REAL,
    supports_claim INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_reviews (
    id TEXT PRIMARY KEY,
    job_item_id TEXT NOT NULL,
    activity_id TEXT NOT NULL,
    review_action TEXT NOT NULL,
    review_note TEXT,
    reviewed_by TEXT,
    created_at TEXT NOT NULL
);

-- ============================================================================
-- Agent Platform Tables (from agent_platform/repository.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_sessions (
    id TEXT PRIMARY KEY,
    domain_type TEXT NOT NULL,
    entry_mode TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    policy_mode TEXT NOT NULL DEFAULT 'standard',
    memory_scope TEXT NOT NULL DEFAULT 'domain',
    title TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_turn_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_turns (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    sequence_no INTEGER NOT NULL,
    tool_name TEXT,
    tool_payload TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_artifacts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    title TEXT,
    content TEXT,
    payload TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_execution_plans (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    source_turn_id TEXT,
    mode TEXT NOT NULL,
    summary TEXT NOT NULL,
    requested_steps TEXT,
    runnable_tools TEXT,
    blocked_tools TEXT,
    risk_flags TEXT,
    reasoning TEXT,
    payload TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_session_states (
    session_id TEXT PRIMARY KEY,
    goal TEXT,
    constraints TEXT,
    preferences TEXT,
    working_memory TEXT,
    current_focus TEXT,
    next_question TEXT,
    next_action TEXT,
    summary TEXT,
    last_tool_names TEXT,
    state_payload TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_insights (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    source_turn_id TEXT,
    insight_type TEXT NOT NULL,
    content TEXT NOT NULL,
    importance REAL NOT NULL DEFAULT 0.5,
    payload TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_thinking_steps (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    source_turn_id TEXT,
    phase TEXT NOT NULL,
    summary TEXT NOT NULL,
    tool_name TEXT,
    payload TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_jobs_v2 (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    domain_type TEXT NOT NULL,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL,
    requested_by TEXT,
    input_payload TEXT,
    result_payload TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_memories (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    source_turn_id TEXT,
    memory_type TEXT NOT NULL,
    content TEXT NOT NULL,
    importance REAL NOT NULL DEFAULT 0.5,
    payload TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_reflections (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    source_turn_id TEXT,
    reflection_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    action_item TEXT,
    score REAL NOT NULL DEFAULT 0.5,
    payload TEXT,
    created_at TEXT NOT NULL
);

-- ============================================================================
-- Product Selection Tables (from product_selection/repository.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS selection_queries (
    id TEXT PRIMARY KEY,
    query_type TEXT NOT NULL,
    query_text TEXT NOT NULL,
    platform_scope TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS selection_opportunities (
    id TEXT PRIMARY KEY,
    query_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    platform_item_id TEXT NOT NULL,
    title TEXT NOT NULL,
    image_url TEXT,
    category_path TEXT,
    price_low REAL,
    price_mid REAL,
    price_high REAL,
    sales_volume INTEGER,
    seller_count INTEGER,
    seller_type TEXT,
    seller_name TEXT,
    demand_score REAL,
    competition_score REAL,
    price_fit_score REAL,
    risk_score REAL,
    cross_platform_signal_score REAL,
    opportunity_score REAL,
    confidence_score REAL,
    risk_tags TEXT,
    reason_blocks TEXT,
    recommended_action TEXT,
    source_urls TEXT,
    source_mode TEXT,
    source_diagnostics TEXT,
    snapshot_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(query_id, platform, platform_item_id)
);

CREATE TABLE IF NOT EXISTS selection_opportunity_signals (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    value_json TEXT NOT NULL,
    sample_size INTEGER DEFAULT 0,
    freshness TEXT,
    reliability REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS selection_tracking_items (
    opportunity_id TEXT PRIMARY KEY,
    is_favorited INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'saved',
    notes TEXT,
    next_action TEXT,
    remind_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- ============================================================================
-- Reward Opportunity Tables (from reward_opportunity/repository.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS reward_source_feeds (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_platform TEXT,
    entry_url TEXT,
    status TEXT NOT NULL DEFAULT 'idle',
    config_json TEXT NOT NULL DEFAULT '{}',
    last_crawled_at TEXT,
    last_success_at TEXT,
    last_error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reward_scout_settings (
    id TEXT PRIMARY KEY,
    query_templates_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reward_discovery_ignored (
    id TEXT PRIMARY KEY,
    dedupe_key TEXT NOT NULL UNIQUE,
    entry_url TEXT NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reward_source_audit (
    id TEXT PRIMARY KEY,
    source_feed_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reward_crawl_jobs (
    id TEXT PRIMARY KEY,
    source_feed_id TEXT NOT NULL,
    status TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'scheduled',
    target_url TEXT,
    document_count INTEGER NOT NULL DEFAULT 0,
    candidate_count INTEGER NOT NULL DEFAULT 0,
    opportunity_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS reward_raw_documents (
    id TEXT PRIMARY KEY,
    crawl_job_id TEXT,
    source_feed_id TEXT,
    source_platform TEXT NOT NULL,
    source_type TEXT,
    source_url TEXT NOT NULL,
    canonical_url TEXT,
    title TEXT NOT NULL,
    body TEXT,
    summary TEXT,
    published_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reward_recall_candidates (
    id TEXT PRIMARY KEY,
    raw_document_id TEXT,
    source_platform TEXT NOT NULL,
    source_url TEXT NOT NULL,
    title TEXT NOT NULL,
    recall_label TEXT NOT NULL,
    recall_reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reward_investigation_runs (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    status TEXT NOT NULL,
    current_round INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reward_investigation_actions (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target_url TEXT,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reward_opportunities (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    normalized_title TEXT,
    source_platform TEXT NOT NULL,
    source_type TEXT,
    source_url TEXT NOT NULL,
    canonical_url TEXT,
    published_at TEXT,
    discovered_at TEXT,
    content_language TEXT,
    raw_text_excerpt TEXT,
    opportunity_type TEXT,
    reward_type TEXT,
    reward_value_text TEXT,
    action_required TEXT,
    eligibility TEXT,
    deadline_text TEXT,
    deadline_at TEXT,
    region_limit TEXT,
    platform_limit TEXT,
    ai_stage_1_recall_reason TEXT,
    ai_stage_2_label TEXT NOT NULL,
    ai_confidence REAL NOT NULL,
    ai_summary TEXT,
    ai_reasoning_brief TEXT,
    ai_missing_evidence TEXT NOT NULL DEFAULT '[]',
    ai_risk_flags TEXT NOT NULL DEFAULT '[]',
    ai_structured_evidence TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'active',
    dedupe_key TEXT,
    content_hash TEXT,
    last_evaluated_at TEXT,
    recheck_after TEXT,
    external_links_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reward_opportunity_evidence (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    snippet TEXT NOT NULL,
    source_url TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reward_evaluation_runs (
    id TEXT PRIMARY KEY,
    candidate_id TEXT,
    opportunity_id TEXT,
    ai_stage_2_label TEXT NOT NULL,
    ai_confidence REAL NOT NULL,
    ai_summary TEXT,
    ai_reasoning_brief TEXT,
    ai_missing_evidence TEXT NOT NULL DEFAULT '[]',
    ai_risk_flags TEXT NOT NULL DEFAULT '[]',
    ai_structured_evidence TEXT NOT NULL DEFAULT '{}',
    needs_investigation INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reward_agent_runs (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    status TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS reward_agent_steps (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL,
    input_json TEXT NOT NULL DEFAULT '{}',
    output_json TEXT NOT NULL DEFAULT '{}',
    latency_ms INTEGER NOT NULL DEFAULT 0,
    failure_type TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reward_tool_calls (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    status TEXT NOT NULL,
    input_json TEXT NOT NULL DEFAULT '{}',
    output_json TEXT NOT NULL DEFAULT '{}',
    latency_ms INTEGER NOT NULL DEFAULT 0,
    failure_type TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reward_evaluator_snapshots (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

-- ============================================================================
-- Indexes - Core Tables
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_activities_source_id ON activities(source_id);
CREATE INDEX IF NOT EXISTS idx_activities_category ON activities(category);
CREATE INDEX IF NOT EXISTS idx_activities_created_at ON activities(created_at);
CREATE INDEX IF NOT EXISTS idx_tracking_status ON tracking_items(status);
CREATE INDEX IF NOT EXISTS idx_digests_digest_date ON digests(digest_date);
CREATE INDEX IF NOT EXISTS idx_digest_candidates_date ON digest_candidates(digest_date);
CREATE INDEX IF NOT EXISTS idx_analysis_templates_default ON analysis_templates(is_default);

-- ============================================================================
-- Indexes - Analysis Agent Tables
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_analysis_job_items_job ON analysis_job_items(job_id);
CREATE INDEX IF NOT EXISTS idx_analysis_job_items_activity ON analysis_job_items(activity_id);
CREATE INDEX IF NOT EXISTS idx_analysis_item_steps_item ON analysis_item_steps(job_item_id);
CREATE INDEX IF NOT EXISTS idx_analysis_evidence_item ON analysis_evidence(job_item_id);
CREATE INDEX IF NOT EXISTS idx_analysis_reviews_item ON analysis_reviews(job_item_id);

-- ============================================================================
-- Indexes - Agent Platform Tables
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_agent_sessions_domain ON agent_sessions(domain_type);
CREATE INDEX IF NOT EXISTS idx_agent_turns_session_seq ON agent_turns(session_id, sequence_no);
CREATE INDEX IF NOT EXISTS idx_agent_artifacts_session ON agent_artifacts(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_execution_plans_session ON agent_execution_plans(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_session_states_session ON agent_session_states(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_insights_session ON agent_insights(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_thinking_steps_session ON agent_thinking_steps(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_jobs_v2_session ON agent_jobs_v2(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_jobs_v2_domain ON agent_jobs_v2(domain_type);
CREATE INDEX IF NOT EXISTS idx_agent_memories_session ON agent_memories(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_reflections_session ON agent_reflections(session_id, created_at);

-- ============================================================================
-- Indexes - Product Selection Tables
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_selection_queries_created ON selection_queries(created_at);
CREATE INDEX IF NOT EXISTS idx_selection_opportunities_query ON selection_opportunities(query_id);
CREATE INDEX IF NOT EXISTS idx_selection_opportunities_platform ON selection_opportunities(platform);
CREATE INDEX IF NOT EXISTS idx_selection_signals_opportunity ON selection_opportunity_signals(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_selection_tracking_status ON selection_tracking_items(status);

-- ============================================================================
-- Indexes - Reward Opportunity Tables
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_reward_candidates_source_url ON reward_recall_candidates(source_url);
CREATE INDEX IF NOT EXISTS idx_reward_runs_candidate ON reward_investigation_runs(candidate_id);
CREATE INDEX IF NOT EXISTS idx_reward_actions_run ON reward_investigation_actions(run_id);
CREATE INDEX IF NOT EXISTS idx_reward_jobs_feed ON reward_crawl_jobs(source_feed_id);
CREATE INDEX IF NOT EXISTS idx_reward_raw_job ON reward_raw_documents(crawl_job_id);
CREATE INDEX IF NOT EXISTS idx_reward_evidence_opp ON reward_opportunity_evidence(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_reward_opps_dedupe ON reward_opportunities(dedupe_key);
CREATE INDEX IF NOT EXISTS idx_reward_audit_source ON reward_source_audit(source_feed_id);
CREATE INDEX IF NOT EXISTS idx_reward_agent_runs_thread ON reward_agent_runs(thread_id);
CREATE INDEX IF NOT EXISTS idx_reward_agent_steps_run ON reward_agent_steps(run_id);
CREATE INDEX IF NOT EXISTS idx_reward_tool_calls_run ON reward_tool_calls(run_id);
CREATE INDEX IF NOT EXISTS idx_reward_evaluator_snapshots_run ON reward_evaluator_snapshots(run_id);
