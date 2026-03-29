# CompressorIQ — Product Roadmap

### From Service Intelligence MVP to Enterprise-Grade Industrial AI Platform

**Version:** 1.0  
**Date:** March 29, 2026  
**Classification:** Confidential — Leadership & Investor Review  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current MVP Scope](#2-current-mvp-scope)
3. [Target Product Vision](#3-target-product-vision)
4. [User Roles & Personas](#4-user-roles--personas)
5. [Capability Roadmap by Phase](#5-capability-roadmap-by-phase)
6. [Data Maturity Roadmap](#6-data-maturity-roadmap)
7. [Analytics Maturity Roadmap](#7-analytics-maturity-roadmap)
8. [Technician Workflow Maturity Roadmap](#8-technician-workflow-maturity-roadmap)
9. [Integration Roadmap](#9-integration-roadmap)
10. [Security & Enterprise Readiness Roadmap](#10-security--enterprise-readiness-roadmap)
11. [Monetization & Commercial Packaging](#11-monetization--commercial-packaging)
12. [Feature Prioritization Table](#12-feature-prioritization-table)
13. [Technical Dependency Map](#13-technical-dependency-map)
14. [Risks & Mitigations](#14-risks--mitigations)
15. [Recommended Pilot Rollout Approach](#15-recommended-pilot-rollout-approach)
16. [KPI Framework for Value Measurement](#16-kpi-framework-for-value-measurement)

---

## 1. Executive Summary

CompressorIQ is a compressor service intelligence platform that transforms unstructured maintenance records into actionable, evidence-based recommendations for field technicians and operations leaders. The current MVP demonstrates a working data ingestion pipeline, a rule-based intelligence engine, and a modern web interface — all built on production-grade architecture.

This roadmap outlines a five-phase evolution from the current single-unit prototype to a fleet-wide, enterprise-scale industrial AI platform capable of serving multiple customers, compressor families, and operational environments.

**The opportunity:** Unplanned compressor downtime costs the oil & gas compression industry an estimated \$2M–\$8M per unit per year in lost production, emergency callouts, and cascading equipment damage. CompressorIQ aims to reduce unplanned downtime by 20–40% through progressively smarter maintenance intelligence — starting with descriptive analytics today and advancing to prescriptive, AI-driven operations within 24 months.

**Current state:** Working MVP with 23-table data model, 10-stage ingestion pipeline, 6-layer intelligence stack, and full-stack web application. Zero trained ML models — intelligence is rule-based, similarity-driven, and fully explainable.

**Target state:** A multi-tenant SaaS platform with real-time sensor integration, trained predictive models, prescriptive maintenance orchestration, and deep ERP/CMMS/SCADA integration — deployable on-premises or in the cloud.

---

## 2. Current MVP Scope

### 2.1 What Exists Today

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CompressorIQ MVP (v0.2.0)                        │
│                                                                         │
│  DATA LAYER                                                             │
│  ├─ 10-stage ingestion pipeline (XLSX/XLS/CSV/TSV → PostgreSQL)        │
│  ├─ 23-table normalized schema (Import / Master / Event / Analytics)   │
│  ├─ SHA-256 file & row fingerprinting for deduplication                │
│  ├─ Full audit trail (raw → normalized traceability)                   │
│  └─ Seeded with 305 rows from Unit MC6068 (single compressor, 6 yrs)  │
│                                                                         │
│  INTELLIGENCE LAYER                                                     │
│  ├─ Layer 1: Descriptive analytics (frequencies, recurrence, intervals)│
│  ├─ Layer 2: Rule-based issue inference (keyword/pattern matching)     │
│  ├─ Layer 3: Weighted similarity scoring (Jaccard + temporal decay)    │
│  ├─ Layer 4: Prescriptive workflow generation (step-by-step guides)    │
│  ├─ Layer 5: Multi-factor confidence scoring (6 auditable factors)     │
│  └─ Layer 5b: Evidence-based plain-language explanations               │
│                                                                         │
│  API LAYER                                                              │
│  ├─ FastAPI REST API (~25 endpoints)                                   │
│  ├─ Import, Events, Compressors, Dashboard, Recommendations, Feedback  │
│  └─ Pydantic v2 request/response validation                           │
│                                                                         │
│  UI LAYER                                                               │
│  ├─ Next.js 16 / React 19 / Tailwind 4 dashboard                     │
│  ├─ Dashboard with KPIs, recent events, recurring issues              │
│  ├─ Machine detail view with timeline and issue frequency              │
│  ├─ Recommendation workflow UI with confidence badges                  │
│  └─ Technician feedback form for outcome capture                      │
│                                                                         │
│  TESTING & DOCS                                                         │
│  ├─ 80+ unit/integration tests (ingestion + intelligence + API)        │
│  └─ Schema docs, pipeline docs, mapping docs, quality rules           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 What Does NOT Exist Yet

| Gap | Impact |
|-----|--------|
| No authentication or authorization | Cannot deploy beyond localhost |
| No trained ML models | "Prediction" is heuristic, not statistical |
| Single compressor dataset (MC6068) | Cannot demonstrate fleet-wide value |
| No real-time sensor data integration | Reactive, not proactive |
| No containerization or CI/CD | Manual deployment only |
| No multi-tenancy | Single-customer architecture |
| Frontend-backend route misalignment | Some UI pages may 404 without proxy |
| No charting/visualization | Data is tabular only, no trend charts |
| No notification or alerting system | Users must manually check the platform |
| No mobile/field-optimized interface | Unusable in the field without connectivity |

### 2.3 Key Architectural Strengths to Build On

1. **Clean separation of concerns** — ingestion, intelligence, API, and UI are fully decoupled
2. **Audit-first data model** — raw data preservation enables future ML retraining
3. **Extensible intelligence stack** — layers can be replaced independently (rules → ML)
4. **Feedback loop infrastructure** — technician outcome data is already captured
5. **Schema supports multi-compressor** — even though current data is single-unit

---

## 3. Target Product Vision

### 3.1 Vision Statement

> **CompressorIQ: The operating system for compressor fleet intelligence.**
>
> Every compressor tells a story through its maintenance history, sensor readings, and operational patterns. CompressorIQ listens, learns, and guides — transforming reactive maintenance into predictive, prescriptive operations that maximize uptime, reduce costs, and keep technicians safe.

### 3.2 Strategic Positioning

```
                    LOW DATA MATURITY ──────────────────── HIGH DATA MATURITY
                           │                                       │
    REACTIVE              │  ┌──────────┐                         │
    (fix when broken)     │  │ MVP TODAY │                         │
                           │  └──────────┘                         │
                           │        ↓                              │
    PREVENTIVE            │     ┌──────────────┐                  │
    (scheduled)           │     │  PHASE 2     │                  │
                           │     └──────────────┘                  │
                           │           ↓                           │
    PREDICTIVE            │        ┌──────────────┐               │
    (condition-based)     │        │  PHASE 3     │               │
                           │        └──────────────┘               │
                           │              ↓                        │
    PRESCRIPTIVE          │           ┌──────────────┐            │
    (autonomous guidance) │           │  PHASE 4     │            │
                           │           └──────────────┘            │
                           │                 ↓                     │
    AUTONOMOUS            │              ┌──────────────┐         │
    (self-optimizing)     │              │  PHASE 5     │         │
                           │              └──────────────┘         │
```

### 3.3 Target Outcomes

| Metric | MVP Baseline | 12-Month Target | 24-Month Target |
|--------|-------------|-----------------|-----------------|
| Unplanned downtime reduction | — | 15–20% | 30–40% |
| Mean time to diagnosis | Manual (hours) | < 30 minutes | < 5 minutes |
| Maintenance cost per unit/year | Baseline | –10% | –25% |
| Technician first-visit resolution rate | ~60% | 75% | 85%+ |
| Recommendation adoption rate | — | 40% | 70%+ |
| Fleet coverage | 1 unit | 50+ units | 500+ units |

---

## 4. User Roles & Personas

### 4.1 Primary Roles

| Role | Description | Key Needs | Phase Available |
|------|-------------|-----------|----------------|
| **Field Technician** | Frontline maintenance personnel dispatched to compressor sites | Mobile-friendly work orders, step-by-step guidance, parts lists, offline access | MVP+ |
| **Maintenance Planner** | Schedules preventive and corrective maintenance across the fleet | Workload visibility, scheduling optimization, resource allocation | Phase 2 |
| **Reliability Engineer** | Analyzes failure patterns and drives root cause elimination | Failure mode analytics, Pareto charts, MTBF/MTTR trends, fleet comparisons | Phase 2 |
| **Operations Manager** | Oversees daily operations for a region or business unit | Fleet health dashboard, cost tracking, SLA compliance, team performance | Phase 2 |
| **VP of Operations / C-Suite** | Strategic decision-making, CAPEX/OPEX planning | Executive dashboards, ROI metrics, fleet lifecycle cost modeling | Phase 3 |
| **Customer (Asset Owner)** | End customer who owns or leases the compressor equipment | SLA reports, uptime guarantees, service transparency | Phase 4 |
| **System Administrator** | Manages platform configuration, users, integrations | User management, SSO config, integration health monitoring | Phase 3 |

### 4.2 Persona Deep Dive — Field Technician (Primary User)

> **Name:** Jake, Senior Compressor Technician  
> **Experience:** 12 years in the field  
> **Environment:** Remote well sites, often limited connectivity  
> **Pain Points:**
> - Arrives at site without full service history — wastes time diagnosing known issues
> - Free-text notes from previous technicians are hard to interpret
> - No visibility into what parts are likely needed before dispatch
> - Repeats work that was already attempted by others
>
> **What CompressorIQ gives Jake:**
> - Pre-arrival briefing with machine history and similar-case outcomes
> - Confidence-scored recommendations ranked by likelihood of resolution
> - Step-by-step workflow with rationale tied to actual evidence
> - Ability to capture structured feedback that improves future recommendations

---

## 5. Capability Roadmap by Phase

### Phase 1: MVP Foundation (Current — Month 0–3)

**Theme:** Prove the data pipeline and intelligence architecture work at single-unit scale.

| Capability | Status | Description |
|-----------|--------|-------------|
| Spreadsheet ingestion pipeline | ✅ Complete | 10-stage pipeline with full audit trail |
| Normalized data model (23 tables) | ✅ Complete | Import / Master / Event / Analytics zones |
| Rule-based issue inference | ✅ Complete | Keyword and pattern-based classification |
| Similarity-based case matching | ✅ Complete | Weighted Jaccard + temporal decay scoring |
| Prescriptive workflow generation | ✅ Complete | Step-by-step guides with evidence |
| Confidence scoring & explanations | ✅ Complete | 6-factor auditable confidence model |
| REST API (25+ endpoints) | ✅ Complete | FastAPI with Pydantic validation |
| Web dashboard | ✅ Complete | Next.js with KPIs, timelines, workflows |
| Technician feedback capture | ✅ Complete | Outcome recording for learning loop |
| Authentication & RBAC | 🔲 Needed | JWT/OAuth2 with role-based access |
| Docker containerization | 🔲 Needed | Multi-stage builds for backend + frontend |
| CI/CD pipeline | 🔲 Needed | Automated test → build → deploy |
| Frontend-backend route alignment | 🔲 Needed | Fix API path mismatches |
| Alembic migration baseline | 🔲 Needed | Stop using `create_all` in production |

**Exit Criteria:** Platform deployable to a controlled pilot environment with authentication, containerization, and stable API contracts.

---

### Phase 2: Operational Pilot (Month 3–9)

**Theme:** Deploy to a real fleet, onboard real users, and validate operational value.

| Capability | Priority | Description |
|-----------|----------|-------------|
| Multi-compressor data import | High | Support N compressor units from multiple spreadsheets |
| Fleet-level dashboard | High | Aggregate health view across all compressors |
| Interactive charts & trends | High | Time-series visualizations (recharts/d3) for failure trends, costs, intervals |
| Maintenance planner view | High | Workload calendar, upcoming PM schedules |
| Reliability analytics | Medium | MTBF, MTTR, failure mode Pareto analysis |
| CSV/PDF data export | Medium | Exportable reports for offline use |
| Notification system | Medium | Alerts for high-severity recurrence signals |
| API versioning (`/api/v1/`) | Medium | Stable contracts for integration partners |
| Structured data collection forms | Medium | Replace free-text with guided input fields |
| Feedback-driven recommendation weighting | High | Actions with better outcomes rank higher |
| Request logging & correlation IDs | Medium | Operational observability |
| Multi-file batch import | Medium | Ingest fleet-wide data from SAP exports |

**Exit Criteria:** 5+ compressor units managed, 3+ active technician users providing feedback, measurable improvement in mean time to diagnosis.

---

### Phase 3: Predictive Maturity (Month 9–18)

**Theme:** Transition from reactive/rule-based to statistically predictive intelligence.

| Capability | Priority | Description |
|-----------|----------|-------------|
| Sensor data ingestion (SCADA/IoT) | Critical | Real-time operating parameters (temp, pressure, vibration, flow) |
| Time-series anomaly detection | High | Statistical/ML models flagging abnormal operating patterns |
| Failure prediction models | High | Supervised models trained on historical failure-to-event sequences |
| Remaining Useful Life (RUL) estimation | High | Survival analysis for critical components |
| NLP on technician notes | High | Sentence-transformer embeddings for semantic similarity (pgvector) |
| Automated root cause analysis | Medium | Causal inference from correlated event patterns |
| Parts demand forecasting | Medium | Predict parts consumption based on fleet failure patterns |
| Mobile-responsive field interface | High | Progressive web app for field use |
| Offline-capable data access | Medium | Service worker caching for remote sites |
| Executive reporting dashboard | Medium | ROI, cost avoidance, fleet performance for leadership |

**Exit Criteria:** At least one trained predictive model in production with measurable accuracy improvement over rule-based baseline. Sensor data flowing for pilot fleet.

---

### Phase 4: Prescriptive Maturity (Month 18–30)

**Theme:** Close the loop — from prediction to automated action orchestration.

| Capability | Priority | Description |
|-----------|----------|-------------|
| Dynamic scheduling optimization | High | AI-optimized maintenance windows balancing cost, risk, and resource availability |
| Digital twin integration | Medium | Virtual compressor models for scenario simulation |
| Automated work order generation | High | Push recommendations directly into CMMS/ERP as work orders |
| Spare parts inventory optimization | High | Just-in-time inventory recommendations based on failure predictions |
| Knowledge graph | Medium | Connected failure mode → root cause → resolution knowledge base |
| Customer-facing SLA dashboards | Medium | Transparency portal for asset owners |
| Multi-tenant architecture | Critical | Isolated data, configurable intelligence per customer |
| Advanced NLP: voice-to-text notes | Low | Field technicians dictate notes via mobile app |

**Exit Criteria:** Automated work order generation active for pilot customers. Maintenance scheduling demonstrably optimized vs. manual planning. Multi-tenant architecture deployed.

---

### Phase 5: Enterprise Scale (Month 30–42)

**Theme:** Scale to hundreds of customers and thousands of compressors.

| Capability | Priority | Description |
|-----------|----------|-------------|
| Horizontal scaling infrastructure | Critical | Kubernetes, auto-scaling, global CDN |
| Federated learning across fleets | High | Learn from all customers without sharing data |
| Self-service customer onboarding | High | Configuration wizard, data mapping templates |
| Marketplace for intelligence modules | Medium | Third-party analytics plugins |
| Regulatory compliance engine | Medium | Emissions, safety, and environmental reporting |
| AR-assisted field guidance | Low | Augmented reality overlays for complex procedures |
| Autonomous maintenance orchestration | Low | Closed-loop: detect → predict → schedule → dispatch → verify |
| White-label / OEM partnerships | Medium | Rebrandable platform for compressor OEMs |

**Exit Criteria:** Platform serving 10+ customers, 1000+ compressor units, with demonstrated unit economics supporting profitable SaaS delivery.

---

## 6. Data Maturity Roadmap

```
Phase 1          Phase 2            Phase 3            Phase 4            Phase 5
MVP FOUNDATION   OPERATIONAL PILOT  PREDICTIVE         PRESCRIPTIVE       ENTERPRISE SCALE
─────────────────────────────────────────────────────────────────────────────────────────

DATA SOURCES
├── Spreadsheets ─── Multi-unit ──── SCADA/IoT ─────── ERP/CMMS ──────── Federated
│   (single unit)    spreadsheets    sensor streams     bi-directional     cross-customer
│                    CSV/SAP exports                    integration        learning
│
DATA VOLUME
├── 305 rows ─────── 5K–50K rows ─── 100K+ rows ────── 1M+ rows ──────── 100M+ rows
│   (1 unit)         (50+ units)      + time-series     + work orders      + fleet-wide
│                                     sensor data       + inventory        aggregation
│
DATA FRESHNESS
├── Static ────────── Batch ───────── Near-real-time ── Real-time ──────── Streaming
│   (manual import)   (daily/weekly)  (hourly ingest)   (sub-minute)       (continuous)
│
DATA QUALITY
├── Basic ─────────── Validated ───── ML-augmented ──── Self-healing ───── Autonomous
│   validation        + dedup         quality scoring    data pipelines     data ops
│   + dedup           + monitoring    + anomaly detect   + auto-correction
│
STORAGE
├── PostgreSQL ────── PostgreSQL ──── + pgvector ─────── + TimescaleDB ──── + Data lake
│   (single node)     (replicated)    + embeddings       or InfluxDB        (Iceberg/Delta)
│                                     + time-series      + object storage    + global CDN
```

### Data Maturity Milestones

| Milestone | Phase | Success Criteria |
|-----------|-------|-----------------|
| Multi-source ingestion | 2 | ≥3 data formats supported (XLSX, CSV, SAP export) |
| Fleet-scale data | 2 | 50+ compressor units with consistent quality |
| Sensor data pipeline | 3 | Real-time data from ≥10 sensors per compressor |
| Embedding-enriched records | 3 | pgvector similarity search operational |
| Bi-directional ERP sync | 4 | Work orders flow back to source systems |
| Cross-customer learning | 5 | Federated model training without data sharing |

---

## 7. Analytics Maturity Roadmap

```
                    ANALYTICS EVOLUTION

Phase 1 ─── DESCRIPTIVE ─── "What happened?"
             │
             ├── Event frequency counts
             ├── Issue category distributions
             ├── Basic recurrence detection
             └── Rule-based issue classification

Phase 2 ─── DIAGNOSTIC ──── "Why did it happen?"
             │
             ├── Failure mode Pareto analysis
             ├── MTBF / MTTR calculations
             ├── Correlation analysis (cost × category × site)
             ├── Technician performance benchmarking
             └── Feedback-weighted recommendation ranking

Phase 3 ─── PREDICTIVE ──── "What will happen?"
             │
             ├── Time-to-failure models (survival analysis)
             ├── Anomaly detection on sensor streams
             ├── NLP-based semantic case matching (embeddings)
             ├── Remaining useful life estimation
             ├── Parts demand forecasting
             └── Risk scoring per compressor

Phase 4 ─── PRESCRIPTIVE ── "What should we do?"
             │
             ├── AI-optimized maintenance scheduling
             ├── Automated work order generation
             ├── Resource allocation optimization
             ├── Scenario simulation (digital twin)
             └── Inventory optimization (just-in-time)

Phase 5 ─── AUTONOMOUS ──── "Do it for me."
             │
             ├── Closed-loop maintenance orchestration
             ├── Self-tuning prediction models
             ├── Federated learning across fleets
             ├── Autonomous anomaly response
             └── Continuous model retraining pipeline
```

### Model Development Sequence

| Model | Training Data Required | Phase | Expected Accuracy |
|-------|----------------------|-------|------------------|
| Issue classifier (NLP) | 1,000+ labeled events | 3 | 85%+ F1 |
| Failure predictor (time-series) | 6+ months sensor data per unit | 3 | 70%+ AUC |
| RUL estimator (survival) | 100+ failure-to-replacement cycles | 3 | ±15% error |
| Anomaly detector (unsupervised) | 30+ days normal operating data | 3 | <5% false positive rate |
| Scheduling optimizer (OR) | 50+ units × 12 months history | 4 | 15%+ cost reduction |
| Parts demand forecaster | 12+ months consumption data | 4 | ±20% accuracy |

---

## 8. Technician Workflow Maturity Roadmap

### Phase 1: Basic Digital Workflow
```
Technician receives a recommendation → Views on desktop → Follows steps → Submits feedback
```
- Static step-by-step guides with evidence
- Manual feedback via web form
- Desktop-only access

### Phase 2: Guided Field Workflow
```
Dispatch alert → Pre-arrival briefing → Guided checklist → Structured data capture → Auto-close
```
- Notification on new recommendations
- Pre-arrival machine summary (history, recent events, common issues)
- Structured input forms replacing free-text
- Photograph attachment for evidence
- Exportable PDF work reports

### Phase 3: Intelligent Field Assistant
```
Predictive alert → Ranked actions → Similar case reference → Parts pre-staged → Outcome tracking
```
- Mobile-responsive progressive web app
- Offline-capable with sync-on-connect
- Semantic search: "show me similar vibration issues on Ariel JGT/2"
- Parts list with availability check
- Voice-to-text note capture

### Phase 4: Orchestrated Maintenance
```
System detects anomaly → Generates work order → Schedules technician → Stages parts → Verifies resolution
```
- Automated dispatch based on technician skills, proximity, and availability
- AR overlays for complex procedures (e.g., valve assembly)
- Real-time collaboration with remote experts
- Automated resolution verification from post-repair sensor data

### Phase 5: Autonomous Operations
```
Continuous monitoring → Self-adjusting schedules → Exception-only human intervention
```
- Technicians intervene only on exceptions
- AI handles routine scheduling, parts ordering, and quality verification
- Continuous improvement loop with minimal human overhead

---

## 9. Integration Roadmap

### Phase-by-Phase Integration Map

```
Phase 1 (MVP)           Phase 2 (Pilot)         Phase 3 (Predictive)
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Spreadsheet     │     │ SAP PM export   │     │ SCADA / OPC-UA  │
│ import (XLSX)   │     │ Maximo CSV      │     │ OSIsoft PI       │
│                 │     │ Email parsing   │     │ Historian APIs   │
│ PostgreSQL      │     │ PostgreSQL      │     │ IoT gateways     │
│ (single node)   │     │ (replicated)    │     │ pgvector         │
└─────────────────┘     └─────────────────┘     │ TimescaleDB      │
                                                 └─────────────────┘

Phase 4 (Prescriptive)  Phase 5 (Enterprise)
┌─────────────────┐     ┌─────────────────┐
│ SAP PM (write)  │     │ Salesforce       │
│ Maximo (write)  │     │ ServiceNow       │
│ Oracle EAM      │     │ Snowflake        │
│ Inventory ERP   │     │ Power BI / embed │
│ Parts suppliers │     │ Partner APIs     │
│ Scheduling tools│     │ Marketplace      │
└─────────────────┘     └─────────────────┘
```

### Integration Priority Matrix

| System | Type | Phase | Effort | Value |
|--------|------|-------|--------|-------|
| SAP Plant Maintenance (read) | ERP | 2 | High | Critical |
| IBM Maximo (read) | CMMS | 2 | High | Critical |
| SCADA / OPC-UA | Sensor | 3 | Very High | Critical |
| OSIsoft PI / Historian | Time-series | 3 | High | High |
| SAP PM (write-back) | ERP | 4 | Very High | High |
| Inventory / procurement | ERP | 4 | High | High |
| SSO (Azure AD / Okta) | Identity | 3 | Medium | Critical |
| Email / Slack notifications | Communication | 2 | Low | Medium |
| Power BI / Tableau | BI | 4 | Medium | Medium |
| Salesforce / ServiceNow | CRM / ITSM | 5 | High | Medium |

---

## 10. Security & Enterprise Readiness Roadmap

### Maturity Progression

| Dimension | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|-----------|---------|---------|---------|---------|---------|
| **Authentication** | JWT tokens | OAuth2 + refresh tokens | SSO (SAML/OIDC) | MFA mandatory | Zero-trust architecture |
| **Authorization** | Role-based (3 roles) | Attribute-based (ABAC) | Row-level security | Customer-scoped tenancy | Delegated admin per tenant |
| **Data Protection** | TLS in transit | + AES-256 at rest | + field-level encryption | + data masking per role | + customer-managed keys |
| **Audit** | Import audit trail | + API request logging | + user action audit log | + compliance reporting | + SOC 2 Type II |
| **Infrastructure** | Docker Compose | Docker + managed DB | Kubernetes + WAF | Multi-region HA | Global deployment |
| **Compliance** | — | — | SOC 2 Type I prep | SOC 2 Type II, ISO 27001 | GDPR, industry-specific |
| **DR / BCP** | Manual backups | Automated daily backups | RPO < 1 hour | RPO < 15 min, RTO < 1 hour | Active-active multi-region |
| **Vulnerability Mgmt** | Dependency scanning | + SAST in CI pipeline | + DAST, pen testing | + bug bounty program | + continuous pen testing |
| **Data Residency** | Single region | Customer-selected region | Per-tenant region config | Geo-fenced data processing | Sovereign cloud support |

### Critical Security Milestones

| Milestone | Phase | Blocker For |
|-----------|-------|------------|
| JWT authentication + RBAC | 1 | Any external deployment |
| TLS everywhere + encrypted at rest | 2 | Pilot with customer data |
| SSO integration (Azure AD) | 3 | Enterprise sales |
| SOC 2 Type I readiness | 3 | Mid-market customers |
| Multi-tenant data isolation | 4 | Multi-customer SaaS |
| SOC 2 Type II certification | 5 | Enterprise contracts |

---

## 11. Monetization & Commercial Packaging

### 11.1 Pricing Tiers

| Tier | Target | Pricing Model | Included Capabilities |
|------|--------|--------------|----------------------|
| **Starter** | Single-site operators, pilot customers | \$500–\$1,500/unit/month | Data ingestion, descriptive analytics, basic recommendations, 5 users |
| **Professional** | Multi-site operators (10–50 units) | \$300–\$800/unit/month (volume discount) | + Predictive models, sensor integration, mobile app, unlimited users |
| **Enterprise** | Fleet operators (50–500+ units) | Custom annual contract | + Prescriptive scheduling, ERP integration, SSO, SLA, dedicated support |
| **OEM Partner** | Compressor manufacturers (white-label) | Revenue share or per-unit license | Full platform, white-labeled, OEM branding, co-development roadmap |

### 11.2 Revenue Model Options

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REVENUE STREAMS                                     │
│                                                                             │
│  PRIMARY                                                                    │
│  ├── SaaS subscription (per-unit/month)                ██████████ 60%      │
│  ├── Implementation & onboarding services              ████       20%      │
│  └── Integration development (ERP/CMMS connectors)     ███        15%      │
│                                                                             │
│  SECONDARY                                                                  │
│  ├── Training & certification programs                 █           3%      │
│  └── Premium analytics add-ons (digital twin, etc.)    █           2%      │
│                                                                             │
│  FUTURE                                                                     │
│  ├── Outcome-based pricing (% of cost savings)                             │
│  ├── Data marketplace (anonymized fleet benchmarks)                        │
│  └── OEM licensing / white-label royalties                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.3 Commercial Packaging Strategy

**Phase 1–2 (Land):** Offer free pilot to 2–3 design partners. The goal is validation, not revenue. Capture testimonials and case studies.

**Phase 3 (Expand):** Convert pilots to paid Starter subscriptions. Upsell to Professional as sensor data integration demonstrates predictive value.

**Phase 4 (Scale):** Introduce Enterprise tier with custom contracts. Begin OEM partnership discussions with compressor manufacturers.

**Phase 5 (Optimize):** Transition top customers to outcome-based pricing (shared savings model). Launch data marketplace for anonymized fleet benchmarks.

### 11.4 Unit Economics Target (Steady State)

| Metric | Target |
|--------|--------|
| Annual contract value (ACV) per customer | \$150K–\$500K |
| Gross margin | 75%+ |
| Customer acquisition cost (CAC) | < 12 months ACV |
| Net revenue retention | 120%+ (expand within account) |
| Churn rate | < 5% annually |

---

## 12. Feature Prioritization Table

Features are scored on Impact (I), Effort (E), Risk (R), and Strategic Value (S) — each on a 1–5 scale. Priority Score = (I × 2 + S × 2 + 5 – E + 5 – R) / 6.

| # | Feature | I | E | R | S | Score | Phase | Dependencies |
|---|---------|---|---|---|---|-------|-------|-------------|
| 1 | Authentication & RBAC | 5 | 2 | 1 | 5 | **4.5** | 1 | None |
| 2 | Docker containerization | 5 | 2 | 1 | 4 | **4.2** | 1 | None |
| 3 | CI/CD pipeline | 4 | 2 | 1 | 4 | **3.8** | 1 | Docker (#2) |
| 4 | Alembic migration baseline | 4 | 1 | 1 | 3 | **3.7** | 1 | None |
| 5 | Frontend-backend route fix | 4 | 1 | 1 | 3 | **3.7** | 1 | None |
| 6 | Multi-compressor import | 5 | 3 | 2 | 5 | **4.0** | 2 | Alembic (#4) |
| 7 | Fleet-level dashboard | 5 | 3 | 2 | 5 | **4.0** | 2 | Multi-comp (#6) |
| 8 | Interactive charts | 4 | 2 | 1 | 4 | **4.2** | 2 | Dashboard (#7) |
| 9 | Feedback-driven weighting | 5 | 2 | 2 | 5 | **4.3** | 2 | Feedback data volume |
| 10 | Notification system | 3 | 2 | 1 | 3 | **3.3** | 2 | Auth (#1) |
| 11 | SCADA/IoT sensor ingestion | 5 | 5 | 4 | 5 | **3.3** | 3 | Time-series DB |
| 12 | NLP embeddings (pgvector) | 5 | 3 | 2 | 5 | **4.0** | 3 | PostgreSQL pgvector |
| 13 | Failure prediction models | 5 | 4 | 3 | 5 | **3.7** | 3 | Sensor data (#11) |
| 14 | Mobile / PWA | 4 | 3 | 2 | 4 | **3.5** | 3 | Auth (#1) |
| 15 | SSO (Azure AD / Okta) | 4 | 3 | 2 | 5 | **3.7** | 3 | Auth (#1) |
| 16 | RUL estimation | 4 | 4 | 3 | 4 | **3.0** | 3 | Sensor data (#11) |
| 17 | Auto work order generation | 5 | 4 | 3 | 5 | **3.7** | 4 | ERP integration |
| 18 | Multi-tenant architecture | 5 | 5 | 4 | 5 | **3.3** | 4 | SSO (#15) |
| 19 | Scheduling optimization | 5 | 4 | 3 | 5 | **3.7** | 4 | Prediction models (#13) |
| 20 | Federated learning | 4 | 5 | 4 | 5 | **3.0** | 5 | Multi-tenant (#18) |

---

## 13. Technical Dependency Map

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      TECHNICAL DEPENDENCY GRAPH                              │
│                                                                              │
│  ┌──────────────────┐                                                        │
│  │ 1. Auth & RBAC   │──────┬──────────────┬──────────────┐                  │
│  └──────────────────┘      │              │              │                  │
│           │                │              │              │                  │
│           ▼                ▼              ▼              ▼                  │
│  ┌──────────────┐  ┌─────────────┐ ┌───────────┐ ┌──────────────┐         │
│  │ 2. Docker    │  │10. Notif.   │ │14. Mobile │ │15. SSO       │         │
│  └──────────────┘  └─────────────┘ └───────────┘ └──────────────┘         │
│           │                                              │                  │
│           ▼                                              ▼                  │
│  ┌──────────────┐                                ┌──────────────┐          │
│  │ 3. CI/CD     │                                │18. Multi-    │          │
│  └──────────────┘                                │    tenant    │          │
│                                                   └──────────────┘          │
│  ┌──────────────┐                                        │                  │
│  │ 4. Alembic   │───────┐                                ▼                  │
│  └──────────────┘       │                        ┌──────────────┐          │
│                          ▼                        │20. Federated │          │
│                  ┌──────────────┐                 │    learning  │          │
│                  │ 6. Multi-    │                 └──────────────┘          │
│                  │    compressor│                                            │
│                  └──────────────┘                                            │
│                          │                                                   │
│                          ▼                                                   │
│                  ┌──────────────┐     ┌──────────────┐                      │
│                  │ 7. Fleet     │     │ 9. Feedback  │                      │
│                  │    dashboard │     │    weighting  │                      │
│                  └──────────────┘     └──────────────┘                      │
│                          │                                                   │
│                          ▼                                                   │
│                  ┌──────────────┐                                            │
│                  │ 8. Charts    │                                            │
│                  └──────────────┘                                            │
│                                                                              │
│  ┌──────────────────────────────────── SENSOR PATH ────────────────────┐    │
│  │                                                                      │    │
│  │  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │    │
│  │  │11. SCADA/IoT │────▶│13. Failure   │────▶│19. Scheduling│        │    │
│  │  │    ingestion  │     │    prediction │     │    optimizer │        │    │
│  │  └──────────────┘     └──────────────┘     └──────────────┘        │    │
│  │         │                                                            │    │
│  │         ▼                                                            │    │
│  │  ┌──────────────┐                                                    │    │
│  │  │16. RUL       │                                                    │    │
│  │  │    estimation │                                                    │    │
│  │  └──────────────┘                                                    │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌──────────────┐                     ┌──────────────┐                      │
│  │12. NLP/      │ (independent path)  │17. Auto work │ (requires ERP)      │
│  │    pgvector  │                     │    orders    │                      │
│  └──────────────┘                     └──────────────┘                      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Critical Path

The longest dependency chain constraining time-to-value:

```
Auth → Docker → CI/CD → Alembic → Multi-comp → Fleet Dashboard → Sensor Ingest → Prediction → Scheduling
 1        2        3        4         6             7               11              13           19
```

Estimated critical path duration: **24–30 months** (can be shortened by parallelizing the sensor and fleet dashboard tracks).

---

## 14. Risks & Mitigations

### 14.1 Technical Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| T1 | **Sensor data quality** is inconsistent across sites, causing false positive anomaly alerts | High | High | Build configurable per-sensor quality thresholds; implement a 30-day calibration period per new data source; human-in-the-loop validation for the first 90 days |
| T2 | **ML model accuracy** is insufficient for customer trust in production decisions | Medium | Critical | Maintain rule-based fallback for all ML-driven features; always show confidence scores and explainability; never automate critical decisions without human approval |
| T3 | **Integration complexity** with legacy ERP/CMMS systems delays deployment | High | High | Start with read-only CSV export integration (Phase 2); build standardized adaptor framework; hire integration specialist |
| T4 | **Scalability bottleneck** in PostgreSQL for time-series sensor data | Medium | Medium | Evaluate TimescaleDB or InfluxDB early (Phase 3 architecture spike); design ingestion layer to be database-agnostic |
| T5 | **Frontend-backend route misalignment** causes pilot deployment failures | High | Medium | Fix immediately in Phase 1; add integration test that validates all frontend API calls against backend routes |

### 14.2 Product & Market Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| P1 | **Technician adoption resistance** — field workers distrust or bypass AI recommendations | High | Critical | Co-design with technicians from Phase 2; never override technician judgment; position as "assistant" not "replacement"; gamify adoption with recognition |
| P2 | **Insufficient historical data** for training accurate predictive models | Medium | High | Augment with industry failure mode databases (e.g., OREDA); use transfer learning from similar rotating equipment; implement few-shot learning techniques |
| P3 | **Competitor products** (Uptake, Augury, SparkCognition) capture market before CompressorIQ matures | Medium | High | Focus on compressor-specific depth vs. horizontal breadth; leverage Enerflex domain expertise; aim for "best for compression" positioning |
| P4 | **Pilot customer expectations** exceed MVP capabilities | High | Medium | Set explicit pilot scope documents; weekly progress demos; transparent roadmap sharing |

### 14.3 Business & Organizational Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| B1 | **Talent shortage** in industrial AI/ML engineering | High | High | Invest in internal training; partner with universities; consider acqui-hire of specialized teams |
| B2 | **Long sales cycles** in enterprise industrial market (6–18 months) | High | Medium | Offer free pilots to design partners; build ROI calculator tool; target VP Operations as economic buyer |
| B3 | **Data privacy concerns** from customers sharing operational data | Medium | High | Offer on-premises deployment option; implement data residency controls; obtain SOC 2 certification |

---

## 15. Recommended Pilot Rollout Approach

### 15.1 Pilot Structure

```
                    PILOT ROLLOUT TIMELINE

Week 1–2:     PREPARATION
               ├── Select 2–3 design partner customers
               ├── Identify 5–10 compressor units per partner
               ├── Deploy containerized platform (Docker Compose)
               ├── Import 12+ months historical data per unit
               └── Train 2–3 technicians per site (30-min onboarding)

Week 3–6:     GUIDED ADOPTION
               ├── Technicians use CompressorIQ alongside existing workflow
               ├── Weekly 15-min check-in calls with each pilot site
               ├── Capture feedback on recommendation quality
               ├── Iterate on UI/UX based on observed usage patterns
               └── Measure: Are technicians actually opening the app?

Week 7–10:    MEASURED VALUE
               ├── Compare diagnosis time: with CompressorIQ vs. without
               ├── Track recommendation acceptance rate
               ├── Measure first-visit resolution improvement
               ├── Document 3+ specific incidents where CIQ added value
               └── Identify top 3 feature requests from technicians

Week 11–12:   DECISION POINT
               ├── Present pilot results to customer leadership
               ├── Publish internal case study with quantified ROI
               ├── Decision: Convert to paid subscription? Expand scope?
               └── Capture design partner testimonial / reference
```

### 15.2 Pilot Site Selection Criteria

| Criterion | Ideal | Acceptable | Reject |
|-----------|-------|-----------|--------|
| Historical data availability | 3+ years per unit | 1+ year per unit | < 6 months |
| Number of compressor units | 10+ at one site | 5+ across 2 sites | < 5 total |
| Technician willingness | Enthusiastic champion | Willing participants | Resistant / skeptical |
| Data format consistency | Standardized SAP/Maximo exports | Mixed spreadsheets | Paper-only records |
| Connectivity | Reliable site internet | Cellular with 4G | No connectivity |
| Management support | VP-level sponsor | Manager-level sponsor | No executive support |

### 15.3 Design Partner Agreement Outline

1. **No-cost access** to CompressorIQ for 12 weeks
2. **Customer commits to:** providing historical data, assigning 2–3 technicians, weekly feedback sessions, participating in case study
3. **CompressorIQ commits to:** dedicated support engineer, weekly product iterations, SLA on bug response (24 hours)
4. **Transition terms:** 20% discount on first-year subscription if pilot converts within 30 days
5. **IP:** All data remains customer property; CompressorIQ retains rights to anonymized, aggregated insights

---

## 16. KPI Framework for Value Measurement

### 16.1 KPI Dashboard Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CompressorIQ VALUE MEASUREMENT                       │
│                                                                         │
│  OPERATIONAL KPIs                   PRODUCT KPIs                       │
│  ┌──────────────────────────┐      ┌──────────────────────────┐       │
│  │ Unplanned downtime hours │      │ Monthly active users      │       │
│  │ Mean time to diagnosis   │      │ Recommendations generated  │       │
│  │ First-visit resolution % │      │ Recommendation acceptance %│       │
│  │ Maintenance cost / unit  │      │ Feedback submission rate   │       │
│  │ Emergency callout count  │      │ Feature adoption heatmap   │       │
│  └──────────────────────────┘      └──────────────────────────┘       │
│                                                                         │
│  FINANCIAL KPIs                     INTELLIGENCE KPIs                  │
│  ┌──────────────────────────┐      ┌──────────────────────────┐       │
│  │ Cost avoidance ($)        │      │ Confidence score accuracy │       │
│  │ Revenue per unit managed  │      │ Similarity match quality  │       │
│  │ Customer acquisition cost │      │ False positive rate       │       │
│  │ Net revenue retention     │      │ Model drift metrics       │       │
│  │ Gross margin %            │      │ Data quality score        │       │
│  └──────────────────────────┘      └──────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 16.2 KPI Definitions & Targets

#### Operational KPIs

| KPI | Definition | Baseline | Phase 2 Target | Phase 3 Target | Phase 5 Target |
|-----|-----------|----------|---------------|---------------|---------------|
| **Unplanned Downtime Hours** | Total hours of unplanned compressor shutdown per unit per quarter | Customer baseline | –10% | –25% | –40% |
| **Mean Time to Diagnosis (MTTD)** | Average time from symptom detection to root cause identification | 4–8 hours (manual) | < 1 hour | < 15 minutes | < 5 minutes |
| **First-Visit Resolution Rate** | % of maintenance events resolved on the first technician visit | ~60% | 70% | 80% | 90% |
| **Maintenance Cost per Unit** | Total maintenance spend (labor + parts + logistics) per compressor per year | Customer baseline | –5% | –15% | –25% |
| **Emergency Callout Rate** | Number of emergency (unscheduled) dispatches per unit per quarter | Customer baseline | –15% | –30% | –50% |

#### Product KPIs

| KPI | Definition | Phase 2 Target | Phase 3 Target | Phase 5 Target |
|-----|-----------|---------------|---------------|---------------|
| **Monthly Active Users (MAU)** | Unique users who perform at least one action per month | 10+ | 100+ | 1,000+ |
| **Recommendation Acceptance Rate** | % of generated recommendations that are acted upon | 30% | 55% | 75% |
| **Feedback Submission Rate** | % of completed work orders with technician feedback | 40% | 65% | 80% |
| **Time in App per Session** | Average minutes per technician session | 5 min | 10 min | 8 min (more efficient) |
| **NPS (Net Promoter Score)** | Technician satisfaction survey score | 20+ | 40+ | 60+ |

#### Financial KPIs

| KPI | Definition | Phase 2 Target | Phase 3 Target | Phase 5 Target |
|-----|-----------|---------------|---------------|---------------|
| **Annual Recurring Revenue (ARR)** | Total annualized subscription revenue | \$200K (pilot conversions) | \$2M | \$20M+ |
| **Cost Avoidance per Customer** | Documented savings from prevented failures | \$50K/year | \$250K/year | \$500K+/year |
| **Gross Margin** | (Revenue – COGS) / Revenue | 60% | 70% | 80% |
| **CAC Payback Period** | Months to recover customer acquisition cost | 18 months | 12 months | 8 months |
| **Net Revenue Retention** | Revenue from existing customers this year / last year | 100% | 115% | 130% |

#### Intelligence KPIs

| KPI | Definition | Phase 2 Target | Phase 3 Target | Phase 5 Target |
|-----|-----------|---------------|---------------|---------------|
| **Recommendation Accuracy** | % of accepted recommendations that resolved the issue (from feedback) | 60% | 75% | 85% |
| **Confidence Calibration** | Correlation between confidence score and actual outcome success rate | 0.3 | 0.6 | 0.8 |
| **False Positive Rate** | % of anomaly/failure alerts that were not actual issues | N/A | < 15% | < 5% |
| **Similar Case Relevance** | % of shown similar cases rated "helpful" by technicians | 40% | 65% | 80% |
| **Data Quality Score** | % of ingested records passing all validation rules | 85% | 92% | 97% |

### 16.3 Measurement Cadence

| Frequency | KPIs Reviewed | Audience |
|-----------|--------------|----------|
| **Daily** | System health, API latency, error rates | Engineering team |
| **Weekly** | MAU, recommendations generated, feedback rate | Product team |
| **Monthly** | All operational + product KPIs | Leadership |
| **Quarterly** | All KPIs including financial + strategic | Executive / investors |
| **Annually** | Full ROI analysis, competitive benchmarking | Board / strategic planning |

---

## Appendix A: Technology Stack Evolution

| Layer | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|-------|---------|---------|---------|---------|---------|
| **Backend** | FastAPI (Python) | FastAPI + Celery | + ML serving (MLflow) | + event streaming | + microservices |
| **Frontend** | Next.js 16, React 19 | + recharts, PWA | + offline mode | + AR SDK | + micro-frontends |
| **Database** | PostgreSQL | PostgreSQL (HA) | + pgvector + TimescaleDB | + Redis cache | + data lake |
| **ML/AI** | Rule engine | + feedback weighting | + scikit-learn, XGBoost, transformers | + optimization (OR) | + federated learning |
| **Infra** | Docker Compose | Docker + CI/CD | Kubernetes | Multi-region K8s | Global K8s + CDN |
| **Monitoring** | Application logs | + structured logging | + Prometheus/Grafana | + APM (Datadog) | + AIOps |

---

## Appendix B: Competitive Landscape

| Competitor | Strengths | Weaknesses vs. CompressorIQ |
|-----------|-----------|----------------------------|
| **Uptake** | Broad industrial AI platform, strong brand | Horizontal (not compression-specific), expensive, long deployment |
| **Augury** | Strong vibration analytics, proven hardware | Requires proprietary sensors, limited to condition monitoring |
| **SparkCognition** | Advanced AI/ML, NLP capabilities | Generalist platform, steep learning curve, high price point |
| **Predii** | Good NLP for maintenance text | Limited industrial deployment, no sensor integration |
| **In-house tools** | Free, customizable | Fragmented, no ML, poor UX, no cross-fleet learning |

**CompressorIQ differentiation:** Compression-specific domain expertise, explainable intelligence (not black-box), technician-centered design, progressive maturity model (value before ML), lower deployment friction.

---

## Appendix C: Glossary

| Term | Definition |
|------|-----------|
| CMMS | Computerized Maintenance Management System |
| MTBF | Mean Time Between Failures |
| MTTR | Mean Time To Repair |
| MTTD | Mean Time To Diagnosis |
| RUL | Remaining Useful Life |
| SCADA | Supervisory Control and Data Acquisition |
| OPC-UA | Open Platform Communications Unified Architecture |
| pgvector | PostgreSQL extension for vector similarity search |
| RBAC | Role-Based Access Control |
| ABAC | Attribute-Based Access Control |
| ACV | Annual Contract Value |
| ARR | Annual Recurring Revenue |
| CAC | Customer Acquisition Cost |
| NPS | Net Promoter Score |
| PWA | Progressive Web Application |
| SOC 2 | Service Organization Control Type 2 audit framework |
| OR | Operations Research (mathematical optimization) |

---

*This document is a living artifact. It should be reviewed and updated quarterly as market conditions, customer feedback, and technical progress inform the roadmap.*

**Prepared by:** CompressorIQ Product Architecture Team  
**Next review date:** June 30, 2026
