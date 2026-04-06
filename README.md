# Agentic CX Simulator

A high-fidelity, containerized OpenEnv environment simulating a high-volume analytics command center and customer service queue.

## Motivation & Real-World Utility
Modern business analytics and quality assurance rely heavily on automated triage. This environment evaluates frontier LLM agents on their ability to act autonomously within a simulated internal network. It requires agents to synthesize business policies, execute SQL-backed data retrieval (CRM), perform RAG (Knowledge Base), and manage progressive conversational state with a simulated user—all while optimizing Average Handle Time (AHT) and avoiding SLA breaches.

## Action & Observation Spaces
- **Action Space**: Strict JSON schema defining `tool` (`query_crm`, `search_kb`, `ask_customer`, `resolve_ticket`) and corresponding parameters.
- **Observation Space**: Continuous feedback including `current_patience` (SLA timer), `last_action_result`, and `conversation_history`.
- **State Verification**: Native SQLite `.db` tracks state mutations for post-episode verifiers.

## Tasks
1. **Easy (The Friendly Upgrade)**: Agent guides a customer through a mid-cycle upgrade by validating prorated charge policies in the KB.
2. **Medium (The Plan Limit Constraint)**: Diagnoses integration errors by cross-referencing plan limits in the CRM against exact KB policies.
3. **Hard (The Strategic Cross-Sell)**: Resolves a storage limit inquiry while identifying a hidden cross-sell opportunity via business logic analytics, actively pitching an add-on.

## Setup & Execution
1. Build container: `docker build -t agentic-cx-simulator .`
2. Run container: `docker run -p 7860:7860 agentic-cx-simulator`
3. Exposes the OpenEnv API spec on `http://localhost:7860`
