# NL/AI querying tools in banking & governance constraints on generative-AI vendors

Compiled 18 Oct 2026 by web search + fetch (no paywalled sources read). Each item is tagged:
**[P]** primary source (vendor docs / regulator), **[S]** secondary (news, law-firm, consultancy), **[V]** vendor marketing / vendor-run benchmark.
Anything not verified against a primary source is said so. Inferences are kept in their own section.

---

## 1. Commercial NL-to-data tools: where the model runs

| Tool | Where the LLM runs | Data-use / residency terms (as documented) | On-prem option? | Licence / tier | Known accuracy limits |
|---|---|---|---|---|---|
| **Power BI Copilot** | Azure OpenAI (Microsoft cloud) | Prompt "isn't used to train any models". If tenant/capacity is outside US or France, Copilot is **off by default** unless admin enables "Data sent to Azure OpenAI can be processed outside your capacity's geographic region, compliance boundary, or national cloud instance" [P] | No evidence of Copilot in Power BI Report Server; Copilot Q&A documented as Power BI *service* only [P/S] | Paid Fabric **F2+** or Premium **P1+**; not on trial SKUs [P]. (Older community posts say F64 — outdated) | MS FAQ itself warns summaries may "fabricate data" when the model has missing values, and Copilot "may answer from the LLM's general knowledge" when the question isn't about the model [P] |
| **Power BI Q&A** (classic NL) | Microsoft service / Desktop (non-generative index) | — | Desktop Q&A supports live connect to on-prem SSAS [P] | Included | **Being retired: "Q&A experiences are going away in February 2027"**, users pointed to Copilot [P]. English only; index caps (5M values, first 1,000 entities) reduce accuracy on big models [P] |
| **Tableau Ask Data** | — | — | — | — | **Retired**: Tableau Cloud Feb 2024, Tableau Server 2024.2; replaced by Tableau Pulse [P] |
| **Tableau Pulse / Tableau Agent (ex-Einstein Copilot)** | Third-party LLMs (OpenAI / Azure OpenAI) via Salesforce Einstein Trust Layer | Zero data retention with LLM partners; not used for training; PII masking on by default; prompts/responses stored in customer's Data Cloud (now "Data 360") for audit [P] | Pulse: Cloud-only per 2024–25 secondary sources [S]. Tableau Agent: reported GA on Tableau Server from 2025.3 [S, unverified against Tableau release notes] — even then the LLM call still leaves for the Trust Layer (inference) | Tableau+ / Cloud+ bundles for some agent features [S] | — |
| **ThoughtSpot Spotter** (Sage retired) | ThoughtSpot-managed LLMs (Azure), or **BYO-LLM** keys (Azure OpenAI, Vertex AI, Bedrock, custom gateway) [P] | ThoughtSpot-provided LLMs "do not retain any data"; zero retention / no training guarantee [P]. Spotter sends **filtered query results** (not just schema) to the LLM; LLM-generated Python cached in Azure 1 h [P] | Spotter documented under ThoughtSpot *Cloud*; no evidence it ships in self-managed ThoughtSpot Software [P-indirect, unconfirmed] | Spotter 3 BYO-LLM requires both Claude and GPT models [P] | Sage EOL and removed (June 2026 cloud release) [P] |
| **Snowflake Cortex Analyst** | LLMs hosted inside Snowflake's service; optional **cross-region inference** | Data at rest stays in home region; with cross-region on, the prompt/response payload is "transmitted transiently to the processing region" (mTLS) [P]. Admin (ACCOUNTADMIN) can restrict regions [P] | No — SaaS only | Billed per message [S] | Snowflake internal benchmark: ~90% vs ~51% for single-prompt GPT-4o [V]; joins post 92% vs 55% [V]. No published independent figure; accuracy depends on curated semantic model + verified queries [P/S] |
| **Databricks AI/BI Genie** | **Partner-powered** (Azure OpenAI) — if the "partner-powered AI features" setting is off, Genie is **unavailable** [P] | Partners use zero-data-retention endpoints; Databricks does not train on prompts/responses (wording narrowed in newer docs to models offered to third parties) [P]. Genie sends NL prompt, table names/descriptions, **relevant values**, example SQL [P] | No — SaaS only | Consumption (DBU) pricing [S] | Docs: "operates in a nondeterministic manner", aim for ≤5 tables per space [S citing docs]. Databricks internal benchmark 84.5% (Genie One) [V] |
| **Amazon Q in QuickSight (now Amazon Quick Suite)** | Amazon Bedrock; cross-Region inference within the same geography [P] | Data stays stored in primary Region but "input prompts and output results may move outside of your primary Region" (within geography) [P]. No-training claim found only in AWS announcements [V] | No | Pro user tier [S, not verified this round] | — |
| **Looker – Gemini / Conversational Analytics** | Google Gemini (Google Cloud) | "Google Cloud does not train models on your prompts or your company's data" [P blog]; data at rest confined to the Looker instance's region [P]; chats stored for history [P] | Looker (Google Cloud core) — no on-prem Gemini | — | **Not in FedRAMP High/Medium boundary**; Google docs say preview features are not recommended for regulated workloads/sensitive data [P] |
| **Oracle Select AI** | Any configured provider (OCI GenAI, OpenAI, Anthropic, Google, Hugging Face…) **or a privately hosted model on a private endpoint (e.g. Ollama/vLLM)** [P] | Data-use = that of chosen provider | **Yes, closest analogue**: runs on Autonomous DB incl. **Exadata Cloud@Customer** (in customer DC); Oracle blog shows private-endpoint self-hosted LLM [P] (C@C + private LLM combo not explicitly confirmed) | Requires Autonomous Database | — |
| **SAP Joule / SAC "Just Ask"** | SAP BTP / generative AI hub (SAP cloud) [S] | Admin controls which models/data Joule sees [P] | No evidence of on-prem | Joule base entitlement [P] | Joule can answer from general knowledge; only answers with source links contain SAP content [P] |

Key URLs
- Power BI/Fabric Copilot FAQ (F2/P1, cross-geo setting, no training): https://learn.microsoft.com/en-us/fabric/fundamentals/copilot-faq-fabric
- Q&A retirement Feb 2027: https://learn.microsoft.com/en-us/power-bi/natural-language/q-and-a-data-sources
- Copilot Q&A service-only: https://learn.microsoft.com/en-gb/power-BI/create-reports/copilot-ask-data-question
- Ask Data retirement: https://help.tableau.com/current/online/en-us/ask_data_enable.htm ; https://www.tableau.com/blog/tableau-metrics-and-natural-language-query-evolve-tableau-pulse
- Tableau Einstein Trust Layer: https://help.tableau.com/current/tableau/en-us/tableau_gai_einstein_trust_layer.htm ; https://www.tableau.com/blog/how-can-i-trust-einstein-copilot-tableau
- Tableau Agent on Server 2025.3 [S]: https://keyrus.com/za/en/insights/why-tableau-server-is-no-longer-the-compromise-choice
- ThoughtSpot Spotter data handling: https://docs.thoughtspot.com/cloud/26.7.0.cl/spotter-data-handling ; BYO-LLM: https://docs.thoughtspot.com/cloud/latest/spotter-byollmk ; enable: https://docs.thoughtspot.com/cloud/latest/spotter-enable ; Sage EOL: https://docs.thoughtspot.com/cloud/26.8.0.cl/26-6-0-cl
- Snowflake cross-region inference: https://docs.snowflake.com/user-guide/snowflake-cortex/cross-region-inference ; Cortex Analyst: https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-analyst ; evaluations: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst-evaluations ; vendor accuracy: https://www.snowflake.com/en/blog/engineering/cortex-analyst-text-to-sql-accuracy-bi/ ; https://venturebeat.com/ai/snowflake-launches-cortex-analyst-an-agentic-ai-system-for-accurate-data-analytics
- Databricks AI trust: https://learn.microsoft.com/en-us/azure/databricks/databricks-ai/databricks-ai-trust ; https://docs.databricks.com/aws/databricksiq/databricksiq-trust ; Genie limits [S]: https://colrows.com/blogs/cortex-analyst-vs-genie/
- Amazon Q in QuickSight cross-region: https://docs.aws.amazon.com/quicksight/latest/user/q-cross-region-inferencing.html
- Looker CA security: https://cloud.google.com/blog/products/business-intelligence/understanding-looker-conversational-analytics-security ; admin/residency: https://docs.cloud.google.com/looker/docs/looker-core-admin-gemini ; overview/FedRAMP: https://docs.cloud.google.com/looker/docs/gemini-overview-looker
- Oracle Select AI: https://docs.oracle.com/en/cloud/paas/autonomous-database/dedicated/hsarg ; providers: https://docs.oracle.com/iaas/releasenotes/autonomous-database-dedicated/adbd-selectai-support.htm ; private endpoint blog: https://blogs.oracle.com/machinelearning/?p=1191
- SAP Joule analytical insights: https://www.sap.com/products/technology-platform/joule-analytical-insights-feature.html ; ref arch: https://architecture.learning.sap.com/docs/ref-arch/9efadc

Accuracy context (enterprise text-to-SQL is hard): frontier models solve only ~6–21% of Spider 2.0 / BEAVER enterprise tasks (cited secondhand: https://answers.databricks.com/ai-tools-multi-table-joins-natural-language-sql ; https://atlan.com/know/ai-agent/data-for-ai/text-to-sql-for-enterprise.md). Microsoft ISE evaluated Genie vs custom agents (custom ~75%): https://devblogs.microsoft.com/ise/llm-sql-query-generation/

---

## 2. Adoption evidence in banking / insurance

- **Bank of England + FCA, 3rd AI survey (Nov 2024)** [P via S]: 75% of firms use AI; foundation models = 17% of use cases; ~one third of use cases are **third-party implementations** (up from 17% in 2022); top-3 providers hold 73% / 44% / 33% of cloud / model / data provision; 46% of firms have only "partial understanding" of the AI they use, largely because of third-party models. https://www.regulationtomorrow.com/2024/11/boe-and-fca-publish-results-of-third-survey-on-ai-in-uk-financial-services/ ; https://www.stephensonharwood.com/insights/the-bank-of-england-and-the-fcas-survey-on-ai-in-uk-financial-services/
- **Evident AI Index 2026 (6 Oct 2026)** [S]: JPMorgan #1 for 5th year, Capital One #2, RBC #3; average score +26% YoY; only 12% of tracked use cases disclose an operational-KPI effect. Outside-in index from public info. https://www.resultsense.com/news/2026-10-07-evident-ai-index-hsbc-drops-out-top-ten/ ; https://www.analyticsinsight.net/news/jpmorgan-tops-banking-ai-rankings-for-5th-straight-year-2026
- **JPMorgan LLM Suite** [S]: in-house wrapper giving ~200k–250k staff governed access to third-party models (OpenAI, Anthropic) "while protecting client data". https://connect.cefpro.com/article/view/inside-jpmorgan-llm-suite-as-ai-agents-spread-across-the-bank ; https://www.artificialintelligence-news.com/news/jpmorgan-chase-ai-strategy-2025/
- **CCAF 2026 Global AI in Financial Services Report** [S]: data privacy/protection and hallucinations are top risk concerns. https://www.smefinanceforum.org/news/11526914
- **CSA draft white paper (Mar 2026)** [S, draft]: data leakage is top AI security concern (61%). https://labs.cloudsecurityalliance.org/agentic/state-of-cloud-and-ai-for-financial-services-2026-v1/
- **Named bank/insurer case studies of Genie / Cortex Analyst / Spotter / Copilot-in-Power-BI: NOT FOUND** in this pass. Only vendor-authored FS guides (e.g. Posit+Snowflake for banks/insurers [V]: https://posit.co/blog/snowflake-cortex-ai-and-posit-for-banks-and-insurers-without-moving-your-data). Treat "banks use these tools" as plausible but undocumented here.

---

## 3. Governance & regulation

### Bank restrictions on public generative AI (2023)
- Feb 2023: **JPMorgan** restricted staff ChatGPT use — "not triggered by any incident … part of controls around third-party software"; **Citigroup** blocked it under automatic third-party-software restrictions; **Goldman** traders restricted; **Deutsche Bank** disabled access; BofA, Wells Fargo also reported [S, citing Bloomberg; Bloomberg original not read]. https://americanbanker.com/articles/wall-streets-chatgpt-nightmare-is-over-before-it-starts-as-banks-crack-down ; https://www.retailbankerinternational.com/news/banking-majors-bar-chatgpt-use/
- May 2023: JPMorgan and Deutsche Bank indicated they'd allow it once vetted; Goldman building own tools [S]. https://fortune.com/2023/05/19/chatgpt-banned-workplace-apple-goldman-risk-privacy
- **Pattern**: these were *internal vendor/third-party-software controls*, later replaced by governed internal platforms (e.g. LLM Suite) — not regulator-ordered bans.

### United States
- **SR 11-7 superseded**: Fed/OCC/FDIC issued **SR 26-2 / OCC Bulletin 2026-13 on 17 Apr 2026**, replacing SR 11-7 and SR 21-8; principle-based; "most relevant" to banks >$30bn assets [P]. https://www.federalreserve.gov/supervisionreg/srletters/sr2602.htm
  - **Generative/agentic AI reportedly carved out of scope** ("novel and rapidly evolving"); agencies plan an RFI on AI incl. GenAI [S — multiple commentaries agree, one disagrees; the attachment SR26-2a1.pdf was not read]. https://www.finos.org/blog/sr-11-7-just-wrote-itself-out-of-the-genai-conversation ; https://elevateconsult.com/insights/sr-11-7-rescinded-model-risk-guidance-ai-gap ; https://www.enz.ai/glossary/sr-26-2
  - **Update project wording**: citing "SR 11-7" as current is now outdated.
- **Interagency Guidance on Third-Party Relationships: Risk Management** (Fed SR 23-4 / OCC / FDIC, 6 Jun 2023; 88 FR 37920) [P]: lifecycle — planning, due diligence, contracting, monitoring, termination; proportional; guidance, not a new rule. Still applies to AI vendors. https://www.federalreserve.gov/supervisionreg/srletters/SR2304.pdf

### European Union
- **EU AI Act** + **Digital Omnibus on AI** (Reg. (EU) 2026/1744, OJ 24 Jul 2026, in force 27 Jul 2026) [S, consistent across law firms]: Annex III stand-alone high-risk (incl. **creditworthiness / credit scoring**, life/health insurance pricing) moved from 2 Aug 2026 to **2 Dec 2027**; Art. 50 transparency applied 2 Aug 2026. https://www.whitecase.com/insight-alert/eu-ai-omnibus-enters-force-amending-ai-act
  - Relevance: an internal NL→SQL analytics assistant is **not itself** an Annex III high-risk use (inference — it isn't credit scoring), so the AI Act is not the main blocker for this project's use case.
- **DORA** (applies since 17 Jan 2025): ICT third-party risk, register of ICT contracts, contractual clauses, exit strategies. ESAs designated **19 critical ICT third-party providers (Nov 2025)** incl. AWS EMEA, Google Cloud EMEA, Microsoft Ireland, Oracle, SAP, IBM, Bloomberg [S]. https://www.tlt.com/insights-and-events/insight/eu-regulators-designate-critical-ict-third-party-providers-under-dora ; https://legal.pwc.de/en/news/articles/esas-publish-first-list-of-critical-ict-third-party-providers-under-dora — i.e. every cloud BI/LLM tool above runs on a designated CTPP.
- **EBA**: 2019 Outsourcing Guidelines being replaced; consultation EBA/CP/2025/12 (Jul–Oct 2025) on **non-ICT** third-party risk, ICT stays under DORA [P]. Final text status not checked. https://eba.europa.eu/publications-and-media/press-releases/eba-launches-consultation-its-draft-guidelines-third-party-risk-management-regard-non-ict-related
- **GDPR**: EDPB Opinion 28/2024 (17 Dec 2024) on personal data in AI models — anonymity case-by-case, legitimate interest needs 3-step test [S]. https://cms.law/en/int/legal-updates/edpb-opinion-28-2024-key-takeaways-on-processing-personal-data-in-the-context-of-ai-models . GDPR permits processors and transfers with safeguards (Arts 28, 44–49) — it does not ban sending data to an LLM vendor (general legal knowledge; not re-sourced this pass).

### United Kingdom
- **PRA SS1/23** Model Risk Management Principles, effective **17 May 2024**, five principles, applies to UK banks/building societies; covers AI/ML models per secondary sources [S; PRA text not read]. https://www.bankofengland.co.uk/prudential-regulation/publication/2023/may/model-risk-management-principles-for-banks-ss (URL not fetched — verify)

### Singapore
- **MAS Guidelines on AI Risk Management for FIs**: final **7 Oct 2026**, effective **7 Oct 2027**; all FIs, all AI; AI inventory, materiality, lifecycle controls; FIs remain accountable for vendor AI and should "limit, suspend or replace" a third-party AI service whose risk exceeds appetite [P + S]. Agentic-AI guidance expected 2027. https://www.mas.gov.sg/regulation/guidelines/guidelines-on-artificial-intelligence-risk-management-for-financial-institutions ; https://www.blockhead.co/2026/10/08/mas-finalises-ai-risk-rules-for-financial-institutions-with-agentic-ai-guidance-to-follow-in-2027/
- FEAT principles (2018) predate this; not re-checked.

### Sri Lanka (CBSL)
- **Banking Act Directions No. 16 of 2021** — Technology Risk Management & Resilience; applies to licensed banks incl. operations via third-party service providers; ISC + CISO required [P]. https://www.cbsl.gov.lk/sites/default/files/cbslweb_documents/laws/cdg/Banking_Act_Directions_No_16_of_2021.pdf
- Amended by **Directions No. 05 of 2023** (redefines third-party service providers) [S]. https://regalert.today/document/b59cb5da-8741-425e-a05c-4cb306f1c7b1
- **Banking Act Direction No. 01 of 2026** (outsourcing), issued 25 Mar 2026, effective **1 Jan 2027**, revokes 2012 outsourcing rules; cloud allowed subject to **data sovereignty**, recoverability, confidentiality, certified providers [S — Daily Mirror; CBSL text not read]. https://www.dailymirror.lk/business-news/Central-Bank-introduces-stringent-rules-on-bank-outsourcing/273-337543 ; https://regalert.today/document/66e88b47-e410-495d-ab38-2a0efc50460f
- LFC equivalent: Finance Business Act Directions No. 01 of 2022.
- Sri Lanka **PDPA No. 9 of 2022** (cross-border transfer rules) — not checked this pass.

### CCPA/CPRA
- Not researched beyond a failed search (CPPA ADMT regulations status as of Oct 2026 unverified). Gap.

---

## 4. "Privacy via local hosting" — is it recognised?
- Vendors themselves concede the boundary matters: Snowflake markets "inside your account / governance boundary", ThoughtSpot sells BYO-LLM so "prompts and data remain within your organization's self-managed cloud environment", Oracle shows private-endpoint self-hosted LLMs for Select AI, Microsoft gates Copilot behind a cross-geo opt-in [P]. That is indirect evidence that *where the model runs* is a purchasing criterion.
- UK: Lloyds and NatWest reportedly in a coalition building a UK **sovereign** model ("Lumen Sovereign", Isambard-AI) [S, aggregator only — verify]. https://algeriatech.news/?p=32850
- On-prem LLM trend statistics found were vendor marketing (e.g. "55% of inference on-prem/edge" — DreamFactory [V], methodology unknown). Do not cite as fact. https://www.dreamfactory.com/hub/on-premise-llm-deployment-statistics
- No regulator found that says on-prem hosting is *required* or *preferred*; regulators are technology-neutral and focus on accountability, third-party risk and concentration (BoE/FCA concentration figures; DORA CTPP regime; MAS "limit, suspend or replace").

---

## 5. Facts vs inferences vs gaps

### Facts (sourced above)
1. Every major BI NL tool (Power BI Copilot, Tableau Pulse/Agent, Spotter, Cortex Analyst, Genie, Amazon Q/Quick, Looker Gemini, SAP Joule) performs LLM inference in a vendor or hyperscaler cloud; several route prompts across regions unless an admin restricts it.
2. All of them advertise no-training / zero-retention terms — so the selling point "your data trains their model" is **not** a valid differentiator for the project.
3. Some send more than schema: Spotter sends filtered result rows; Genie sends "relevant values"; Copilot can fall back to general knowledge.
4. Only Oracle Select AI (Autonomous DB on Exadata Cloud@Customer + private LLM endpoint) comes close to an in-DC deployment; it requires Oracle Autonomous DB.
5. Power BI Q&A is retiring Feb 2027; Tableau Ask Data retired 2024; ThoughtSpot Sage EOL 2026 — the market moved wholesale from on-prem-capable classic NL to cloud LLM features.
6. 2023 bank ChatGPT restrictions were framed as internal third-party-software controls, not regulatory orders.
7. SR 11-7 was replaced by SR 26-2 (Apr 2026); EU high-risk AI deadlines moved to Dec 2027; MAS AI guidelines finalised Oct 2026; CBSL outsourcing direction effective Jan 2027.

### Inferences
- **The project's framing is supported**: no regulation found that bans sending bank data to a generative-AI vendor. Restrictions come from (a) institution-level vendor/third-party-risk and AI-governance policy (JPMorgan/Citi 2023 wording), (b) regulator *guidance* that makes the bank accountable for the vendor (US interagency TPRM, MAS, DORA, CBSL 16/2021 & 01/2026), and (c) data-protection and residency obligations (GDPR transfers, CBSL "data sovereignty" condition for cloud). Suggested wording: "Supervisory frameworks do not prohibit generative-AI vendors, but they place full accountability for vendor AI on the institution (due diligence, contractual rights, exit plans, residency), which internal AI-governance policies translate into restrictions or lengthy approval for a newer, less-precedented vendor category."
- The US carve-out of GenAI from SR 26-2 *increases* uncertainty rather than removing it — banks without supervisory guidance tend to apply conservative internal policy (inference; supported only by commentary).
- Differentiators that hold up: (1) inference never leaves the institution's data centre (no cross-region switch, no CTPP dependency, no sub-processor chain); (2) no licence tie to a specific warehouse/BI capacity (F2/P1, Snowflake, Databricks, Autonomous DB); (3) works against the bank's existing operational DBs. Differentiators that do **not** hold: "vendors train on your data" (they contractually don't); "cloud is illegal".
- Honest counterpoint for the dissertation: commercial tools have curated semantic layers and large models; the local SLM will likely be less accurate, and vendor accuracy claims (~84–92%) are internal benchmarks not comparable to Spider/BIRD.

### Gaps / to verify before citing
- SR 26-2 attachment text (confirm GenAI exclusion wording) and OCC Bulletin 2026-13.
- PRA SS1/23 text (AI coverage); EBA final non-ICT TPRM guidelines (published?); CBSL Direction 01/2026 primary PDF; Sri Lanka PDPA transfer provisions; CCPA/CPPA ADMT rules status.
- Pricing for Amazon Quick Suite, Genie, Tableau+ not verified this round.
- Tableau Agent on Tableau Server 2025.3 — only secondary source.
- Whether ThoughtSpot Software (self-managed) has Spotter.
- No independent named bank/insurer case studies for any tool found; Bloomberg original (Feb 2023) not read.
- No independent accuracy benchmark of Copilot/Genie/Cortex Analyst on a public dataset found.
- DORA CTPP list date (18 vs 19 Nov 2025) — check ESMA/EBA primary.
