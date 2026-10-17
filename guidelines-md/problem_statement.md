# Project Specification: Civic Fix — Civic Issue Reporting Platform

## 1. Project Metadata
- **Project Name:** Civic Fix
- **Domain:** Civic Tech / Urban Planning
- **Target Audience:** Citizens, Local Municipal Authorities, Maintenance Field Teams

---

## 2. Objective & Background
Citizens often face challenges when reporting local civic issues, identifying the appropriate municipal authorities, and tracking complaint resolution status. 

**Goal:** Build a centralized, end-to-end civic issue reporting platform where citizens can submit local problems (e.g., potholes, water leaks, overflowing garbage, broken streetlights) and responsible teams can efficiently assign, manage, and resolve them.

---

## 3. Core Requirements & Features

### 3.1 Citizen Capabilities
- **Issue Submission:**
  - Mandatory field inputs: Title, Description, Category (e.g., Roads, Sanitation, Water, Lighting), Location (GPS coordinates / Address).
  - Media attachment support (Photo/Image upload).
- **Proximity & Duplicate Search:**
  - View nearby reported issues on a visual map or list interface.
  - Ability to detect/upvote existing duplicate reports before creating a new entry.
- **Citizen Dashboard:**
  - Real-time status tracking for submitted issues (`Reported` -> `In Progress` -> `Resolved`).
  - History of reports and upvoted issues.

### 3.2 Administrative & Maintenance Capabilities
- **Issue Lifecycle Management:**
  - Assign reported issues to specific operational teams or department representatives.
  - Update issue status along with resolution logs/notes and optional resolution proof images.
- **Analytics & Metrics Dashboard:**
  - Display aggregated statistics (Total reported, open vs. resolved cases).
  - Track Average Resolution Time (ART) grouped by category and urgency.

### 3.3 Automated Logic & Intelligence
- **Automated Prioritization System:**
  - Compute a dynamic priority score using:
    $$\text{Priority Score} = f(\text{Severity}, \text{Community Impact / Upvotes}, \text{Time Unresolved})$$
- **Duplicate Detection Logic:**
  - Flag potential duplicate submissions using geographical proximity thresholds and category similarity matching.

---

## 4. Technical Constraints & Data Requirements

### Key Entities
1. **User:** `id`, `name`, `role` (`citizen`, `admin`, `field_agent`), `email`
2. **Issue:** `id`, `title`, `description`, `category_id`, `latitude`, `longitude`, `media_urls`, `status`, `priority_score`, `created_at`, `updated_at`, `assigned_team_id`
3. **Upvote / Duplicate Link:** `id`, `issue_id`, `user_id`
4. **Resolution Log:** `id`, `issue_id`, `notes`, `proof_media_url`, `resolved_at`, `agent_id`

---

## 5. Execution Steps for AI Agent
1. **Schema Design:** Define data models/migrations matching the key entities listed above.
2. **API/Backend Setup:** Implement RESTful or GraphQL endpoints for authentication, issue CRUD, location querying, and state transitions.
3. **Priority & Duplicate Algorithm:** Implement backend functions to compute dynamic priority scores and flag spatial/textual duplicates.
4. **UI Implementation:** Build responsive interfaces for Citizen Submission, Citizen Dashboard, Admin Task Assignment, and Analytics Overview.