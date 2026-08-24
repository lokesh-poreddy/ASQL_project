-- =============================================================================
-- NEXUS-SQL | 08_seed.sql
-- Layer: SEED DATA  –  Research areas, venues, and 30 representative papers
-- for smoke-tests and baseline experiments. Papers are intentionally spread
-- across years, citation counts, areas, and venues so every query type in
-- the benchmark has non-empty result sets.
-- =============================================================================

-- ── Research areas ────────────────────────────────────────────────────────────
INSERT INTO research_areas (area_id, area_name, description) VALUES
    (1, 'Natural Language Processing',  'Computational processing of human language');
INSERT INTO research_areas (area_id, area_name, description) VALUES
    (2, 'Computer Vision',              'Image and video understanding');
INSERT INTO research_areas (area_id, area_name, description) VALUES
    (3, 'Database Systems',             'Data storage, query processing, and optimization');
INSERT INTO research_areas (area_id, area_name, description) VALUES
    (4, 'Distributed Systems',          'Networked computing and consensus');
INSERT INTO research_areas (area_id, area_name, description) VALUES
    (5, 'Cardiac Signal Processing',    'ECG/EEG analysis and biomedical signal processing');
INSERT INTO research_areas (area_id, area_name, description) VALUES
    (6, 'Machine Learning Theory',      'Statistical learning, optimization, and generalization');
INSERT INTO research_areas (area_id, area_name, description) VALUES
    (7, 'Information Retrieval',        'Search engines, ranking, and recommendation');
INSERT INTO research_areas (area_id, area_name, description) VALUES
    (8, 'Human-Computer Interaction',   'Usability and interface design');
INSERT INTO research_areas (area_id, area_name, description) VALUES
    (9, 'Robotics',                     'Autonomous systems and motion planning');
INSERT INTO research_areas (area_id, area_name, description) VALUES
    (10,'Computer Networks',            'Protocols, routing, and network architecture');

-- ── Venues ────────────────────────────────────────────────────────────────────
INSERT INTO venues (venue_id, venue_name, venue_type) VALUES (1, 'NeurIPS',  'CONFERENCE');
INSERT INTO venues (venue_id, venue_name, venue_type) VALUES (2, 'ACL',      'CONFERENCE');
INSERT INTO venues (venue_id, venue_name, venue_type) VALUES (3, 'VLDB',     'CONFERENCE');
INSERT INTO venues (venue_id, venue_name, venue_type) VALUES (4, 'SIGMOD',   'CONFERENCE');
INSERT INTO venues (venue_id, venue_name, venue_type) VALUES (5, 'ICML',     'CONFERENCE');
INSERT INTO venues (venue_id, venue_name, venue_type) VALUES (6, 'IEEE TBME','JOURNAL');
INSERT INTO venues (venue_id, venue_name, venue_type) VALUES (7, 'JMLR',     'JOURNAL');
INSERT INTO venues (venue_id, venue_name, venue_type) VALUES (8, 'arXiv',    'PREPRINT_SERVER');
INSERT INTO venues (venue_id, venue_name, venue_type) VALUES (9, 'EMNLP',    'CONFERENCE');
INSERT INTO venues (venue_id, venue_name, venue_type) VALUES (10,'ICLR',     'CONFERENCE');

-- ── Authors ───────────────────────────────────────────────────────────────────
INSERT INTO authors (author_id, full_name, normalized_name) VALUES (1,  'Ashish Vaswani',     'vaswani ashish');
INSERT INTO authors (author_id, full_name, normalized_name) VALUES (2,  'Noam Shazeer',       'shazeer noam');
INSERT INTO authors (author_id, full_name, normalized_name) VALUES (3,  'Jacob Devlin',       'devlin jacob');
INSERT INTO authors (author_id, full_name, normalized_name) VALUES (4,  'Ming-Wei Chang',     'chang ming-wei');
INSERT INTO authors (author_id, full_name, normalized_name) VALUES (5,  'Yann LeCun',         'lecun yann');
INSERT INTO authors (author_id, full_name, normalized_name) VALUES (6,  'Geoffrey Hinton',    'hinton geoffrey');
INSERT INTO authors (author_id, full_name, normalized_name) VALUES (7,  'Yoshua Bengio',      'bengio yoshua');
INSERT INTO authors (author_id, full_name, normalized_name) VALUES (8,  'Rajat Monga',        'monga rajat');
INSERT INTO authors (author_id, full_name, normalized_name) VALUES (9,  'Haixun Wang',        'wang haixun');
INSERT INTO authors (author_id, full_name, normalized_name) VALUES (10, 'Peng Liu',           'liu peng');
INSERT INTO authors (author_id, full_name, normalized_name) VALUES (11, 'Arun Kumar',         'kumar arun');
INSERT INTO authors (author_id, full_name, normalized_name) VALUES (12, 'Sarah Johnson',      'johnson sarah');
INSERT INTO authors (author_id, full_name, normalized_name) VALUES (13, 'Mohamed Ismail',     'ismail mohamed');
INSERT INTO authors (author_id, full_name, normalized_name) VALUES (14, 'Lena Fischer',       'fischer lena');
INSERT INTO authors (author_id, full_name, normalized_name) VALUES (15, 'Carlos Mendes',      'mendes carlos');

-- ── Papers ────────────────────────────────────────────────────────────────────
-- Spread: years 2018-2025, citations 0-15000, all 10 areas, various venues
INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (1,'P-00001',
    'Attention Is All You Need',
    'We propose a new simple network architecture, the Transformer, based solely on attention mechanisms.',
    2017, 1, 15000, 1, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (2,'P-00002',
    'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
    'We introduce BERT, designed to pre-train deep bidirectional representations from unlabeled text.',
    2019, 2, 12000, 1, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (3,'P-00003',
    'Deep Residual Learning for Image Recognition',
    'We present a residual learning framework to ease the training of deep neural networks.',
    2016, 1, 18000, 2, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (4,'P-00004',
    'Transformer-Based ECG Analysis for Cardiac Arrhythmia Detection',
    'We apply transformer attention mechanisms to 12-lead ECG signals for arrhythmia classification.',
    2023, 6, 340, 5, 'ARTICLE');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (5,'P-00005',
    'Scalable Distributed SQL Query Processing',
    'A new approach to distributed query planning that minimises cross-node data shuffles.',
    2022, 3, 89, 3, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (6,'P-00006',
    'Neural Information Retrieval: A Survey',
    'Survey of neural approaches to document retrieval and ranking.',
    2021, 8, 450, 7, 'PREPRINT');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (7,'P-00007',
    'Hybrid Vector-SQL Retrieval for Scientific Literature',
    'Combines SQL filtering with dense vector similarity for hybrid information retrieval.',
    2024, 8, 22, 7, 'PREPRINT');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (8,'P-00008',
    'Learned Query Optimisation in Relational Databases',
    'A reinforcement learning approach to cardinality estimation and join ordering.',
    2024, 4, 130, 3, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (9,'P-00009',
    'Quantised Vector Embeddings for Low-Memory Retrieval',
    'INT8 quantisation of sentence embeddings with minimal recall loss.',
    2025, 10, 18, 6, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (10,'P-00010',
    'ECG Signal Segmentation Using Self-Supervised Transformers',
    'Self-supervised pretraining on large ECG datasets for downstream cardiac diagnosis.',
    2024, 6, 77, 5, 'ARTICLE');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (11,'P-00011',
    'Adaptive Index Tuning for OLAP Workloads',
    'Automated index selection driven by workload replay and cost modelling.',
    2023, 3, 56, 3, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (12,'P-00012',
    'Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks',
    'Combines a dense retriever with a sequence-to-sequence model for open-domain QA.',
    2020, 1, 6200, 1, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (13,'P-00013',
    'Robust Consensus in Byzantine Fault-Tolerant Distributed Systems',
    'A formally verified BFT consensus protocol with sub-linear message complexity.',
    2022, 8, 34, 4, 'PREPRINT');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (14,'P-00014',
    'Vision Transformer: An Image Is Worth 16x16 Words',
    'Applying transformer architecture directly to image patches for classification.',
    2021, 10, 9800, 2, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (15,'P-00015',
    'Generalisation Bounds for Deep Networks via PAC-Bayes',
    'Tight PAC-Bayes bounds for stochastic deep neural networks.',
    2025, 5, 11, 6, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (16,'P-00016',
    'Dense Passage Retrieval for Open-Domain Question Answering',
    'Training dual-encoder dense retrievers with in-batch negative sampling.',
    2020, 9, 5100, 7, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (17,'P-00017',
    'Conversational SQL: Translating Natural Language to SQL Queries',
    'A seq2seq model for multi-turn NL-to-SQL translation with conversation history.',
    2023, 2, 210, 1, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (18,'P-00018',
    'Approximate Nearest Neighbour Search with HNSW Graphs',
    'Hierarchical navigable small world graphs for scalable ANN search.',
    2018, 8, 3400, 7, 'PREPRINT');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (19,'P-00019',
    'Multi-Label ECG Classification with Convolutional Networks',
    'CNN architecture for simultaneous detection of multiple ECG abnormalities.',
    2022, 6, 155, 5, 'ARTICLE');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (20,'P-00020',
    'Natural Language Interfaces to Databases: A Survey',
    'Survey of 30 years of NL-to-SQL and NL-to-DB research.',
    2023, 8, 88, 1, 'PREPRINT');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (21,'P-00021',
    'Efficient Transformers: A Survey',
    'Survey of techniques to reduce the O(n^2) attention complexity of transformers.',
    2022, 7, 2300, 6, 'ARTICLE');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (22,'P-00022',
    'Colosseum: Benchmarking NL-to-SQL Systems on Real-World Databases',
    'A new benchmark for evaluating NL-to-SQL on real enterprise schemas.',
    2025, 4, 9, 3, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (23,'P-00023',
    'Robotic Grasping with Semantic Scene Understanding',
    'Combining object detection and semantic mapping for dexterous robotic manipulation.',
    2024, 1, 45, 9, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (24,'P-00024',
    'Low-Latency Network Routing with Deep Reinforcement Learning',
    'RL-based adaptive routing outperforms OSPF on congested backbone networks.',
    2023, 8, 67, 10, 'PREPRINT');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (25,'P-00025',
    'Conversational Search: Querying the Web via Dialogue',
    'Mixed-initiative dialogue systems for interactive web search sessions.',
    2021, 9, 310, 7, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (26,'P-00026',
    'Adaptive Compression for Learned Vector Indexes',
    'Dynamic precision selection (FP32/FP16/INT8) for vector index storage-recall tradeoffs.',
    2025, 10, 5, 7, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (27,'P-00027',
    'Query-Aware Data Partitioning in Distributed Databases',
    'Partitioning strategy that co-locates data likely to be queried together.',
    2024, 3, 102, 3, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (28,'P-00028',
    'Cardiac Risk Stratification with Multi-Modal Learning',
    'Combining ECG, imaging, and clinical text for cardiac risk prediction.',
    2025, 6, 3, 5, 'ARTICLE');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (29,'P-00029',
    'Causal Inference in Machine Learning: A Unified Framework',
    'Bridging the gap between causal models and predictive ML algorithms.',
    2024, 5, 198, 6, 'CONFERENCE_PAPER');

INSERT INTO papers (paper_id,paper_code,title,abstract,year,venue_id,citation_count,primary_research_area_id,publication_type)
VALUES (30,'P-00030',
    'NEXUS-SQL: Adaptive Hybrid Retrieval over Scientific Literature',
    'NL-to-SQL system with hybrid SQL/vector retrieval and resource-aware optimisation.',
    2025, 8, 1, 7, 'PREPRINT');

-- ── Paper-Author links ────────────────────────────────────────────────────────
INSERT INTO paper_authors VALUES (1, 1, 1);
INSERT INTO paper_authors VALUES (1, 2, 2);
INSERT INTO paper_authors VALUES (2, 3, 1);
INSERT INTO paper_authors VALUES (2, 4, 2);
INSERT INTO paper_authors VALUES (3, 5, 1);
INSERT INTO paper_authors VALUES (4, 10, 1);
INSERT INTO paper_authors VALUES (5, 11, 1);
INSERT INTO paper_authors VALUES (6, 12, 1);
INSERT INTO paper_authors VALUES (7, 13, 1);
INSERT INTO paper_authors VALUES (8, 9, 1);

-- ── Keywords ─────────────────────────────────────────────────────────────────
INSERT INTO keywords (keyword_id, keyword_text) VALUES (1,  'transformer');
INSERT INTO keywords (keyword_id, keyword_text) VALUES (2,  'attention mechanism');
INSERT INTO keywords (keyword_id, keyword_text) VALUES (3,  'ECG');
INSERT INTO keywords (keyword_id, keyword_text) VALUES (4,  'natural language processing');
INSERT INTO keywords (keyword_id, keyword_text) VALUES (5,  'SQL');
INSERT INTO keywords (keyword_id, keyword_text) VALUES (6,  'vector search');
INSERT INTO keywords (keyword_id, keyword_text) VALUES (7,  'information retrieval');
INSERT INTO keywords (keyword_id, keyword_text) VALUES (8,  'deep learning');
INSERT INTO keywords (keyword_id, keyword_text) VALUES (9,  'hybrid retrieval');
INSERT INTO keywords (keyword_id, keyword_text) VALUES (10, 'quantization');
INSERT INTO keywords (keyword_id, keyword_text) VALUES (11, 'cardiac');
INSERT INTO keywords (keyword_id, keyword_text) VALUES (12, 'NL-to-SQL');
INSERT INTO keywords (keyword_id, keyword_text) VALUES (13, 'approximate nearest neighbour');
INSERT INTO keywords (keyword_id, keyword_text) VALUES (14, 'distributed systems');
INSERT INTO keywords (keyword_id, keyword_text) VALUES (15, 'database');

-- ── Paper-Keyword links ───────────────────────────────────────────────────────
INSERT INTO paper_keywords VALUES (1,  1);  -- Attention → transformer
INSERT INTO paper_keywords VALUES (1,  2);  -- Attention → attention mechanism
INSERT INTO paper_keywords VALUES (2,  1);  -- BERT → transformer
INSERT INTO paper_keywords VALUES (2,  4);  -- BERT → NLP
INSERT INTO paper_keywords VALUES (4,  1);  -- ECG transformer → transformer
INSERT INTO paper_keywords VALUES (4,  3);  -- ECG transformer → ECG
INSERT INTO paper_keywords VALUES (4, 11);  -- ECG transformer → cardiac
INSERT INTO paper_keywords VALUES (7,  5);  -- Hybrid → SQL
INSERT INTO paper_keywords VALUES (7,  6);  -- Hybrid → vector search
INSERT INTO paper_keywords VALUES (7,  9);  -- Hybrid → hybrid retrieval
INSERT INTO paper_keywords VALUES (9,  6);  -- Quantised → vector search
INSERT INTO paper_keywords VALUES (9, 10);  -- Quantised → quantization
INSERT INTO paper_keywords VALUES (18, 6);  -- HNSW → vector search
INSERT INTO paper_keywords VALUES (18,13);  -- HNSW → ANN
INSERT INTO paper_keywords VALUES (30, 5);  -- NEXUS → SQL
INSERT INTO paper_keywords VALUES (30, 9);  -- NEXUS → hybrid retrieval
INSERT INTO paper_keywords VALUES (30,12);  -- NEXUS → NL-to-SQL

COMMIT;

PROMPT Seed data inserted. Run nexus_refresh_mviews to refresh materialized views.
