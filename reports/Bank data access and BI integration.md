# Bank data access and BI integration

Research report for J26-DS-336. Written 18 Oct 2026 from three note files in `research_notes/Bank data access and BI integration/` (`current_practice.md`, `nl_tools_and_governance.md`, `bi_integration.md`). Those notes were compiled from web search the same day. No source was re-checked for this report, and no paywalled source was read. Every figure below carries the link given in the notes.

Source tags used throughout:
- **[vendor]** vendor-published or vendor-sponsored material, or a vendor's own benchmark. Treat figures as marketing, not evidence.
- **[secondary]** seen only in press coverage, a law-firm note or a search excerpt; the primary document was not read.
- **[inference]** our reasoning, not a sourced fact.

---

## 1. Short answer

1. **How they get answers today.** Smaller US banks and credit unions mostly reach data through their outsourced core vendor and through spreadsheets; only about two in five have a warehouse or data lake. Ad hoc questions go to small IT, finance or BI staff, and data talent is the biggest skills gap. Self-service BI has not removed the analyst bottleneck in any industry. Evidence for mid-size insurers and FinTechs is thin and mostly vendor case studies.
2. **How they are adopting NL/AI querying.** Every major BI vendor now sells a natural-language assistant (Power BI Copilot, Tableau Agent, ThoughtSpot Spotter, Snowflake Cortex Analyst, Databricks Genie, Amazon Q, Looker Gemini, SAP Joule). All of them run the model in a vendor or hyperscaler cloud. The older, on-prem-capable NL features are being retired. We found no named bank or insurer case study for any of these tools.
3. **Under what constraints.** Generative-AI vendors are restricted mainly by the institution's own AI-governance and vendor-risk policy, reinforced by regulator guidance that makes the institution accountable for its vendors. No regulation we found bans sending bank data to a generative-AI vendor, and no regulator requires or prefers on-prem hosting.
4. **How our system differs.** Our model runs inside the institution's data centre, has no licence tie to a particular warehouse or BI platform, and works against an existing operational or reporting database. It is much less accurate today (0.43 execution accuracy with a stand-in model), and its privacy argument has to rest on where inference runs, not on vendors training on customer data (they contractually do not).
5. **BI integration.** Yes, and it should be a two-tier design: our chat page is the **explore** tier, and an analyst **promotes** a good answer into a frozen, reviewed SQL query that becomes a governed view or a BI chart. The language model must never sit on the dashboard refresh path. A 1-2 day prototype with Apache Superset is feasible (section 7).

---

## 2. How target organisations get answers from internal data today

### 2.1 US community and regional banks (best evidence)

The **Bank Director 2025 Technology Survey** [vendor: sponsored by Jack Henry] covered 141 executives and directors at US banks under $100B assets, fielded June-July 2025, over half from $1B-$10B banks. Primary PDF: https://www.bankdirector.com/wp-content/uploads/2025/09/2025TechReport-OpenVersion.pdf

How banks manage their data (select all that apply):

| Practice | Share |
|---|---|
| Keep data in the system or platform that generates or uses it | 56% |
| Rely on their core provider to access their data | 56% |
| Use spreadsheets to manage data used by business lines | 41% |
| Use a data lake or warehouse to combine sources | 39% |
| Have no formal data management strategy | 23% |

Other findings from the same survey:
- 33% name "inability to use data effectively" as a top-3 technology concern.
- 28% invested in data analysis platforms in the past 18 months, rising to 70% for banks over $10B. Larger banks are "much more likely" to say they use analytics effectively.
- Data strategy and management is the area most needing in-house expertise (46%, the top answer). Among banks that say technology is under-resourced, 47% lack mid-level staff such as programmers and data scientists.

**Core-vendor dependence.** Fiserv, FIS and Jack Henry together served over 70% of surveyed banks (2022) and nearly half of surveyed credit unions (2020) (Kansas City Fed, March 2024 [secondary for the figures]): https://www.kansascityfed.org/research/payments-system-research-briefings/market-structure-of-core-banking-services-providers/ . An ABA survey reported banks citing "ability to access data" as a problem with core providers [secondary]: https://bankingjournal.aba.com/2023/02/aba-survey-fewer-than-half-of-banks-satisfied-with-core-provider/

**Data maturity.** The Cornerstone Advisors / KlariVis "Data EQ" study [vendor: commissioned by KlariVis, a bank BI vendor] scored 124 US banks and credit unions ($250M-$10B) at an average 241/500; credit unions 271, banks 211; $500M-$1B institutions scored lower than smaller peers: https://www.crnrstone.com/press-release/new-cornerstone-advisors-research-finds-community-banks-and-credit-unions-only-halfway-to-successfully-leveraging-their-data

### 2.2 Credit unions

- Credit unions scored higher than banks on Data EQ (above).
- Shared or CUSO-run warehouses exist as a product category, e.g. CU*Answers' warehouse on CU*BASE core data [vendor]: https://www.cuanswers.com/wp-content/uploads/ai-datawarehouse_1page-sales.pdf
- No current CUNA, Callahan or Filene survey with BI or warehouse adoption figures was found. The newest figures are old vendor or 2021 material (Finalytics.ai 2022 [vendor]: only 12% able to use internal and external data to drive outcomes, https://www.cubroadcast.com/episodes/2851-finalyticsai-survey-reveals-14-credit-unions-have-proper-approach-to-execute-digital-strategy).

### 2.3 Mid-size insurers (thin evidence)

- PwC (undated): nearly 40% of mid-size insurers ($500M-$2B NWP) put policy administration system replacement in their top three initiatives: https://www.pwc.com/en_US/us/financial-services/publications/viewpoints/assets/fs-viewpoint-fire-ready-aim-pas-transformation.pdf
- Innovation Vista (2026 edition): mid-market insurers are stronger on data/BI maturity than on AI: https://innovationvista.com/metrics/insur-analytics-maturity-survey
- The widely quoted "86% dissatisfied with analytics capabilities" (BriteCore 2025 [vendor]) appears only in a second vendor's blog and is **unverified**: https://www.globenewswire.com/news-release/2025/10/29/3176360/0/en/BriteCore-Releases-2025-P-C-Core-Systems-Report-Highlighting-Industry-Shifts-Toward-Integration-Analytics-and-AI.html

### 2.4 Growth-stage FinTechs (vendor case studies only)

No survey of FinTech data stacks was found. Case studies [vendor] describe cloud warehouses plus Looker, Metabase or Superset, and a small data team acting as a bottleneck:
- Yellow Card: a four-person data team "had become a bottleneck for everyday questions": https://www.metabase.com/case-studies/yellowcard
- Pipe moved from Looker to Preset (Superset) over semantic-layer maintenance and per-seat cost: https://preset.io/blog/transitioning-from-looker-to-preset-to-enable-self-serve-analytics/

### 2.5 Sri Lanka

One small qualitative study (n=5, private commercial banks): banks mainly use Power BI and Tableau, most started analytics in the last 3-4 years, and are "still in the early stages of business analytics maturity" (Rodrigo, Hettiarachchi and Kumarasinghe, 2024): https://jbt.sljol.info/articles/114

### 2.6 The analyst bottleneck is not solved by self-service BI (cross-industry)

- Only 25% of employees actively use BI tools on average, with minimal growth over seven years; NL query was a usage driver for only 14% (BARC/Eckerson, survey late 2021 [vendor-sponsored]): https://barc.com/news/new-study-identifies-drivers-of-bi-and-analytics-adoption-in-companies-today/
- Dresner (2025 interview): average BI penetration "still below 40%": https://www.datacamp.com/podcast/the-state-of-bi-in-2025
- Gartner (May 2024 abstract): business users are "underprepared" for self-service analytics "even with GenAI-enabled natural language interactions, due to insufficient data literacy training": https://www.gartner.com/en/documents/5448363
- Gartner (Mar 2026 abstract): organisations are "increasingly looking to move analytics use cases from dashboards to GenAI-fueled natural language query experiences", with semantic layers as a prerequisite: https://www.gartner.com/en/documents/7632029

### 2.7 Typical stack (synthesis)

| Layer | Smaller banks / credit unions | Mid-size insurers | Growth-stage FinTech |
|---|---|---|---|
| System of record | Outsourced core; data often reached through the core provider | Legacy policy admin, claims and billing systems | Own cloud product database |
| Integration | Data left in source systems; warehouse in about 39% | Data lake / warehouse projects | Cloud warehouse + ELT |
| Reporting | Core-vendor reports, vendor BI add-ons, Power BI / Tableau, spreadsheets | Power BI etc.; regulatory reporting | Looker, Metabase, Superset |
| Who answers ad hoc questions | Small IT / finance staff | IT / actuarial / BI teams (no figures) | Small data team |

Confidence is high for the US bank column and low for insurers and FinTechs. We found **no** current figure for how long an ad hoc data request takes in banks or insurers; the only figure (days to weeks) is a 2015 ThoughtSpot survey [vendor]: https://www.thoughtspot.com/blog/top-5-takeaways-our-2015-bi-survey

### 2.8 What this means for us [inference]

- The gap at these institutions is people and integration more than dashboards. An NL-to-SQL tool addresses the people gap, but it **assumes a queryable, integrated database**, which only about 39% of the surveyed banks have. This is a precondition we must state.
- With 56% relying on the core vendor for data access, our appliance would usually sit over a vendor extract or reporting database, not the core itself. Those schemas tend to have wide tables and abbreviated column names, which is the setting where our TPC-H column-recall weakness appeared.
- NL-to-SQL lowers the SQL barrier. It does not make users interpret results correctly (Gartner, above).

---

## 3. How they are adopting NL/AI querying tools

### 3.1 The commercial tools all run the model in a vendor cloud

| Tool | Where the model runs | Data-use terms (documented) | On-prem option |
|---|---|---|---|
| Power BI Copilot | Azure OpenAI | Prompt not used to train models; off by default outside US/France unless an admin allows cross-geo processing ([docs](https://learn.microsoft.com/en-us/fabric/fundamentals/copilot-faq-fabric)) | No evidence for Power BI Report Server |
| Tableau Pulse / Tableau Agent | Third-party LLMs via Salesforce Einstein Trust Layer | Zero retention, no training, PII masking by default ([docs](https://help.tableau.com/current/tableau/en-us/tableau_gai_einstein_trust_layer.htm)) | Agent reportedly on Tableau Server 2025.3 [secondary], but inference still leaves for the Trust Layer |
| ThoughtSpot Spotter | ThoughtSpot-managed Azure LLMs or bring-your-own LLM key | No retention; sends **filtered result rows**, not just schema ([docs](https://docs.thoughtspot.com/cloud/26.7.0.cl/spotter-data-handling)) | Documented for Cloud only |
| Snowflake Cortex Analyst | Inside Snowflake; optional cross-region inference | Payload "transmitted transiently" to another region if enabled ([docs](https://docs.snowflake.com/user-guide/snowflake-cortex/cross-region-inference)) | No (SaaS) |
| Databricks AI/BI Genie | Partner-powered (Azure OpenAI); unavailable if that setting is off | Zero-retention endpoints; sends table descriptions, **relevant values**, example SQL ([docs](https://learn.microsoft.com/en-us/azure/databricks/databricks-ai/databricks-ai-trust)) | No (SaaS) |
| Amazon Q in QuickSight | Amazon Bedrock | Prompts and outputs "may move outside of your primary Region" within the geography ([docs](https://docs.aws.amazon.com/quicksight/latest/user/q-cross-region-inferencing.html)) | No |
| Looker Gemini | Google Cloud | No training on prompts ([blog](https://cloud.google.com/blog/products/business-intelligence/understanding-looker-conversational-analytics-security)); preview features not recommended for regulated data ([docs](https://docs.cloud.google.com/looker/docs/gemini-overview-looker)) | No |
| Oracle Select AI | Any configured provider, **or a privately hosted model on a private endpoint** ([docs](https://docs.oracle.com/en/cloud/paas/autonomous-database/dedicated/hsarg)) | Depends on provider | **Closest analogue**: Autonomous DB, including Exadata Cloud@Customer; requires Oracle Autonomous Database |
| Metabase Metabot | Cloud, BYO key, and since v64 (Oct 2026) "an open model you host yourself with vLLM" ([releases](https://www.metabase.com/releases-ai)) | Depends on provider | **Yes, now fully local is possible.** Direct comparable; must go in related work |

The classic, on-prem-capable NL features are being retired: Power BI Q&A "going away in February 2027" ([docs](https://learn.microsoft.com/en-us/power-bi/natural-language/q-and-a-data-sources)); Tableau Ask Data retired in 2024 ([docs](https://help.tableau.com/current/online/en-us/ask_data_enable.htm)); ThoughtSpot Sage end-of-life in 2026 ([docs](https://docs.thoughtspot.com/cloud/26.8.0.cl/26-6-0-cl)).

**Vendor accuracy claims** are internal benchmarks [vendor] and not comparable to Spider or BIRD: Snowflake reports about 90% for Cortex Analyst vs about 51% for single-prompt GPT-4o ([blog](https://www.snowflake.com/en/blog/engineering/cortex-analyst-text-to-sql-accuracy-bi/)); Databricks reports 84.5% for Genie. Independent context: frontier models solve only about 6-21% of Spider 2.0 / BEAVER enterprise tasks [secondary]: https://atlan.com/know/ai-agent/data-for-ai/text-to-sql-for-enterprise.md

### 3.2 Adoption in banking and insurance

- UK: 75% of firms use AI; foundation models are 17% of use cases; about one third of use cases are third-party implementations; 46% of firms have only a "partial understanding" of the AI they use, largely because of third-party models (Bank of England and FCA, Nov 2024 [secondary]): https://www.regulationtomorrow.com/2024/11/boe-and-fca-publish-results-of-third-survey-on-ai-in-uk-financial-services/
- US: 49% of banks and 59% of credit unions report deployed generative AI (Cornerstone, Jan 2026 [vendor-adjacent]): https://www.crnrstone.com/press-release/cornerstone-advisors-whats-going-on-in-banking-research-finds-ai-crypto-and-fraud-are-top-of-mind-for-banking-executives-in-2026 . But 52% of Bank Director respondents use generative AI in none of the listed functions. The samples and definitions differ, so never quote one figure without the other.
- Large banks build governed internal wrappers around third-party models, e.g. JPMorgan's LLM Suite [secondary]: https://connect.cefpro.com/article/view/inside-jpmorgan-llm-suite-as-ai-agents-spread-across-the-bank
- Data privacy, hallucination and data leakage are the top AI risk concerns (CCAF 2026 [secondary], https://www.smefinanceforum.org/news/11526914 ; CSA draft 2026, 61% data leakage [secondary, draft], https://labs.cloudsecurityalliance.org/agentic/state-of-cloud-and-ai-for-financial-services-2026-v1/).
- **No named bank or insurer case study** of Copilot, Genie, Cortex Analyst or Spotter was found. "Banks use these tools" is plausible but undocumented.

---

## 4. Governance constraints

### 4.1 Restrictions come from internal policy, not a legal ban

- In 2023 JPMorgan restricted staff ChatGPT use as part of "normal controls around third-party software", not because of an incident; Citigroup, Goldman Sachs, Deutsche Bank, Bank of America and Wells Fargo were reported doing similar [secondary, citing Bloomberg]: https://www.americanbanker.com/articles/jpmorgan-restricts-staffs-use-of-ai-powered-chatgpt-bot . Several later allowed vetted use or built internal platforms: https://fortune.com/2023/05/19/chatgpt-banned-workplace-apple-goldman-risk-privacy
- In 2025, 66% of surveyed US banks had an AI acceptable-use policy, 41% had updated vendor due diligence for AI risk, and 15% had restricted or banned AI tools pending evaluation (Bank Director, above).

### 4.2 Regulation makes the institution accountable for its vendors

- **US.** SR 26-2 / OCC Bulletin 2026-13 (17 Apr 2026) replaced SR 11-7 and SR 21-8 on model risk; it is principle-based and "most relevant" to banks over $30bn: https://www.federalreserve.gov/supervisionreg/srletters/sr2602.htm . Generative and agentic AI are reportedly carved out of its scope pending an RFI [secondary; commentaries mostly agree, one disagrees; attachment not read]: https://www.finos.org/blog/sr-11-7-just-wrote-itself-out-of-the-genai-conversation . The 2023 Interagency Guidance on Third-Party Relationships still applies to AI vendors: https://www.federalreserve.gov/supervisionreg/srletters/SR2304.pdf
- **EU.** DORA (since 17 Jan 2025) governs ICT third-party risk; the ESAs designated 19 critical ICT third-party providers in Nov 2025, including AWS, Google Cloud, Microsoft, Oracle and SAP [secondary]: https://www.tlt.com/insights-and-events/insight/eu-regulators-designate-critical-ict-third-party-providers-under-dora . The AI Act's Annex III high-risk deadlines (including credit scoring) moved to 2 Dec 2027 [secondary]: https://www.whitecase.com/insight-alert/eu-ai-omnibus-enters-force-amending-ai-act . An internal NL-to-SQL assistant is not itself an Annex III use [inference]. GDPR allows processors and transfers with safeguards; it does not ban sending data to an LLM vendor (general legal knowledge, not re-sourced).
- **UK.** PRA SS1/23 model risk principles, effective 17 May 2024 [secondary; PRA text not read].
- **Singapore.** MAS AI Risk Management Guidelines, final 7 Oct 2026, effective 7 Oct 2027; FIs stay accountable for vendor AI and should "limit, suspend or replace" a third-party AI service whose risk exceeds appetite: https://www.mas.gov.sg/regulation/guidelines/guidelines-on-artificial-intelligence-risk-management-for-financial-institutions
- **Sri Lanka.** CBSL Banking Act Directions No. 16 of 2021 (technology risk, including third-party providers): https://www.cbsl.gov.lk/sites/default/files/cbslweb_documents/laws/cdg/Banking_Act_Directions_No_16_of_2021.pdf . Banking Act Direction No. 01 of 2026 on outsourcing, effective 1 Jan 2027, allows cloud subject to **data sovereignty** and other conditions [secondary; CBSL text not read]: https://www.dailymirror.lk/business-news/Central-Bank-introduces-stringent-rules-on-bank-outsourcing/273-337543

### 4.3 What the evidence does and does not support

Supported: supervisory frameworks do not prohibit generative-AI vendors, but they place full accountability for vendor AI on the institution (due diligence, contract rights, exit plans, residency). Internal AI-governance policy turns that into restrictions or long approval cycles for a newer, less-precedented vendor category. Vendors themselves treat where the model runs as a buying criterion: Microsoft gates Copilot behind a cross-geo opt-in, ThoughtSpot sells bring-your-own-LLM, Oracle and Metabase support self-hosted models.

**Not supported:**
- **No regulator requires or prefers on-prem hosting.** Regulators are technology-neutral and focus on accountability, third-party risk and concentration.
- **No source shows a bank choosing a local model over a cloud tool for this reason.** It is an argument, not a finding.
- On-prem LLM trend statistics found were vendor marketing (e.g. DreamFactory's "55% of inference on-prem/edge" [vendor], https://www.dreamfactory.com/hub/on-premise-llm-deployment-statistics). Do not cite them.

---

## 5. How our system differs from and fits alongside existing systems

### 5.1 Comparison

| | Core-vendor reporting / reporting APIs | BI dashboards (Power BI, Tableau, Superset) | Analyst-written SQL | Commercial NL tools (Copilot, Genie, Cortex Analyst, Spotter) | Our appliance |
|---|---|---|---|---|---|
| **Where the model runs** | No model | No model (classic) | No model | Vendor or hyperscaler cloud; some route across regions unless restricted (section 3.1) | Inside the institution's data centre, on mid-range hardware |
| **Ad hoc questions** | Only what the vendor exposes | Only what the BI team built; Q&A-style NL features being retired | Yes, but queued behind a small team | Yes | Yes |
| **Accuracy / correctness** | Deterministic, vendor-validated | Deterministic once built and reviewed | As good as the analyst; reviewable | Vendor claims about 84-92% on internal benchmarks [vendor]; depend on curated semantic models; Genie documented as non-deterministic | 0.43 execution accuracy on 128 Chinook + Spider questions with a stand-in model; non-deterministic; no semantic layer |
| **Cost / licence** | Bundled with the core contract | BI licences (Power BI Report Server comes with SQL Server 2025 Enterprise/Standard; Superset is Apache-2.0) | Staff time | Tied to a platform tier: Fabric F2+ / Premium P1+, Snowflake per message, Databricks DBU, Oracle Autonomous DB | Appliance licence; no tie to a warehouse or BI platform |
| **On-prem fit** | Depends on core deployment | Yes for Report Server, Tableau Server, Superset, Metabase | Yes | No, except Oracle Select AI (Cloud@Customer + private model) and Metabase Metabot (self-hosted model, v64) | Yes, by design |

Sources for the cost row: Power BI Report Server licensing https://learn.microsoft.com/sql/reporting-services/reporting-services-consolidation-faq?view=sql-server-ver17 ; Copilot tiers https://learn.microsoft.com/en-us/fabric/fundamentals/copilot-faq-fabric . Snowflake and Databricks pricing models are [secondary] and not verified.

### 5.2 Differentiators that hold up

1. Inference never leaves the institution's data centre: no cross-region switch, no dependence on a designated critical cloud provider, no sub-processor chain to put through vendor due diligence.
2. No licence tie to a specific warehouse or BI capacity.
3. It works against the database the institution already has, including a core-vendor reporting extract.
4. Active schema pruning reduces what the model sees, which matters most when the model is not local; for us it is defence in depth plus a token saving (about 16% at equal column recall in Phase 8).

### 5.3 What does not favour us

1. **Vendors do not train on customer data.** Every tool in section 3.1 advertises no-training or zero-retention terms. "Your data will train their model" is not a valid argument.
2. **No regulator requires on-prem.** Our case rests on internal governance cost and institutional preference, not on compliance necessity.
3. **We are no longer the only local option.** Oracle Select AI with a private model and Metabase Metabot with a self-hosted vLLM model both run inside the institution. Our differentiation from them is no platform tie (Oracle) and the measured pipeline (retrieval/pruning, fine-tuning, quantization), not locality alone.
4. **Accuracy gap.** 0.43 execution accuracy is far below what any analyst or deterministic dashboard delivers, and below vendor claims (even allowing that those are not comparable). A wrong number in a bank is worse than no number.
5. **Warehouse precondition.** About 61% of the surveyed banks have no warehouse or lake; our system needs a single queryable database.
6. **Data literacy.** Gartner says NL interfaces do not fix literacy. Users can still misread a correct answer or trust a wrong one.
7. **Row-level security.** The current harness queries as one read-only account, so it does not enforce the institution's per-user access rules (section 6.3).

### 5.4 Where it fits [inference]

Our system is an **explore tool for staff who cannot write SQL**, sitting next to existing dashboards, not replacing them. Dashboards stay the source of record for recurring, reviewed numbers. Our system answers the one-off question that today goes into an analyst's queue, and the analyst reviews and promotes the useful answers. In the market's terms, it is a standalone NL-to-SQL engine (like Vanna, Dataherald, the Wren engine) rather than a BI-native assistant (like Metabot), so integration should be BI-agnostic.

---

## 6. BI dashboard integration

### 6.1 Can it integrate? Yes, if the BI tool is self-hosted

| BI product | On-prem? | Usable mechanisms |
|---|---|---|
| Power BI Report Server | Yes | DirectQuery or scheduled refresh from a SQL view (SQL Server, Oracle, PostgreSQL); `Web.Contents` refresh of a fixed **GET** URL (POST is anonymous only, no OAuth, no dynamic URLs); iframe embed with `?rs:Embed=true` ([data sources](https://learn.microsoft.com/power-bi/report-server/data-sources), [Web.Contents](https://learn.microsoft.com/powerquery-m/web-contents), [embedding](https://learn.microsoft.com/power-bi/report-server/developer-handbook-overview)) |
| Power BI Service | No, cloud | Query results go to Microsoft's cloud through the gateway. Out of scope unless the institution's AI-governance policy already approves it |
| Tableau Server | Yes | Hyper API to publish extracts ([docs](https://help.tableau.com/current/api/hyper_api/en-us)); REST API Connector (GET, extract-only; Server support unconfirmed) ([listing](https://exchange.tableau.com/products/1111)); Embedding API v3 with connected-app JWT ([docs](https://help.tableau.com/current/api/embedding_api/en-us/docs/embedding_api_auth.html)). **Do not use WDC 3.0**: archived and removed in Tableau 26.3 ([repo](https://github.com/tableau/wdc3)) |
| Apache Superset | Yes (Apache-2.0) | REST API to create datasets and charts; guest-token embedding with RLS clauses, token fetched server-side ([API](https://superset.apache.org/docs/api), [embedding](https://superset.apache.org/user-docs/using-superset/embedding)) |
| Metabase | Yes (AGPL OSS) | `POST /api/card` for native SQL questions ([API](https://www.metabase.com/learn/administration/metabase-api)); guest embedding with signed JWT, but no row/column security in guest embeds ([docs](https://www.metabase.com/docs/latest/embedding/guest-embedding)) |
| Grafana | Yes (AGPL) | Infinity data source can POST to our `/query` (use 3.4.1+ for CVE-2025-8341) ([docs](https://grafana.com/docs/plugins/yesoreyeram-infinity-datasource/latest/advanced-features/url/)). Easy demo, but banks rarely use Grafana for business BI |

Avoid Power BI push/streaming datasets (cloud-only and being retired: https://learn.microsoft.com/power-bi/connect-data/service-real-time-streaming). A Power BI custom visual that calls our API is unverified and high-risk.

### 6.2 Integration patterns

| Pattern | Verdict |
|---|---|
| (a) Chat answer → "save as chart" through the BI tool's API | Good: users explore, then promote. Needs a BI service account and review before sharing |
| (b) Chat page and BI dashboard side by side (iframe embed) | Good for display; works with every self-hosted tool. It is "dashboard in our page", not "chat in the dashboard" |
| (c) Approved SQL → governed DB view or BI dataset | **Best governance**: reuses DB grants and RLS, normal change control, the BI tool never calls the model. Slow and human-in-the-loop |
| (d) BI tool calls our service as a live data source | **Avoid with live generation.** The model is non-deterministic, so a dashboard number could change because the SQL changed, not the data. Acceptable only when the endpoint replays frozen, stored SQL |

### 6.3 Recommended pattern: explore, then promote

1. **Explore.** Staff ask questions in our chat page. Read-only, logged, statement guard and timeout as today.
2. **Promote.** An analyst reviews a good answer and clicks "save". The service stores the **frozen SQL** with an id. From there it either becomes a governed DB view that Power BI Report Server reads via DirectQuery (Microsoft shops), or a Superset chart / Metabase question created through their API (open-source shops). A fixed `GET /answers/{id}.csv` that replays the stored SQL serves Power BI `Web.Contents`, Tableau's REST connector, Grafana and Excel.
3. **Display.** Embed existing dashboards next to the chat.

Rule: **the language model is never on the dashboard refresh path.** Dashboards run reviewed, deterministic SQL under the institution's normal access controls.

Security requirements for any pattern:
- **Run queries under the user's role.** One shared service account bypasses the institution's row-level security. Use the end user's DB identity or one read-only login per role. Superset guest tokens and Metabase locked parameters apply filters the host app chooses, so we are responsible for mapping user to filter.
- **Keep the existing guard** (SELECT/WITH only, read-only connection, timeout). Promotion adds a second gate: human review.
- **Extend the audit log** with user id, answer id and BI artefact id, so any dashboard number traces back to question → SQL → model version.
- **Keep secrets server-side** (Superset guest-token calls, Metabase embedding secret).
- **Watch for egress traps**: the Power BI Service gateway, and Power BI Desktop for Report Server contacting `pbivisuals.powerbi.com` for custom visuals.

---

## 7. Prototype plan (about 1-2 days)

Stack: existing harness + Apache Superset in Docker on the same machine, pointing at Chinook. Superset is chosen because it is Apache-2.0, self-hosted, and has both a REST API and embedding.

1. **Chart hint.** Add a `chart` field to the `POST /query` response from a simple rule: one text column + one numeric → bar; date + numeric → line; otherwise table. No model involved.
2. **Saved answers.** Add `POST /answers` to store `{question, sql, db, user, created}` and return an id. Add `GET /answers/{id}.csv`, which replays the stored SQL through the existing read-only executor without regenerating it.
3. **Promote to Superset.** Add `POST /answers/{id}/superset`: log in, create a virtual dataset from the stored SQL, create a chart with the suggested type, return its URL. Check the exact payloads against the instance's own `/swagger/v1` first.
4. **UI.** In `chat.html`, add "Save as chart" after a successful answer and show the created chart in an iframe (`standalone=1`).
5. **Evidence for the dissertation.** Log `answer_id` and `chart_id` in `handoff.log.jsonl`. Show that replaying `/answers/{id}.csv` returns identical rows across runs, while regenerating from the same question may not. This turns the determinism argument into a measured result.

Left out on purpose: live Power BI and Tableau demos (licences, Windows and Kerberos setup). Describe them on paper using the GET CSV endpoint and the DirectQuery-to-view path. Per-user RLS can be simulated with one read-only DB user per role if the panel asks.

---

## 8. Implications for the dissertation

### 8.1 Claims to make

- Supervisory frameworks do not prohibit generative-AI vendors, but they make the institution fully accountable for vendor AI (due diligence, contract rights, exit plans, data residency). Internal AI-governance policy turns that into restrictions or long approvals for a newer, less-precedented vendor category. A local system removes the vendor from that review.
- The market moved from on-prem-capable classic NL (Power BI Q&A, Tableau Ask Data, ThoughtSpot Sage, all retiring) to cloud-hosted generative assistants, leaving a gap for institutions whose policy keeps them on-prem.
- Our system complements dashboards: explore with NL, promote reviewed SQL into governed BI.

### 8.2 Wording to change

1. **SR 11-7.** SR 11-7 was superseded by **SR 26-2 / OCC Bulletin 2026-13 on 17 Apr 2026**. Our proposals do not currently cite SR 11-7 (checked: no mention in the repo's proposal and scope documents), but do not add it as current guidance. If US model risk is cited, cite SR 26-2 and note that generative AI is reportedly outside its scope pending an RFI (verify first). That carve-out increases uncertainty for banks rather than removing restrictions [inference].
2. **"Training-data use" as an open question.** The Combined Proposal (paragraph on restrictions, ~line 108) and Project Scope (line 17) list "training-data use" among the open questions about generative-AI vendors. All major vendors now contractually exclude training on customer data. Reword to: "concerns about where inference runs, cross-region processing, what context is sent (some tools send result rows or column values), and the sub-processor chain."
3. **"Restricted at most such organisations"** (Combined Proposal, Ekanayake proposal ~line 89). The evidence is softer: 66% have an AI use policy, 41% updated vendor due diligence, 15% restricted or banned AI tools. Say "subject to AI-governance and vendor-risk review at most such organisations", and cite Bank Director.
4. **"What those existing tools can't do is run without sending schema and data to a hosted LLM"** (Project Scope, line 38). No longer true: Oracle Select AI supports a private model endpoint, and Metabase v64 supports a self-hosted vLLM model. Say "most commercial NL tools run the model in the vendor's cloud; the few local options are tied to a specific database (Oracle) or BI platform (Metabase)."
5. **"Wait days or weeks"** (Project Scope, line 38). The only source is a 2015 vendor survey. Either cite it as such or say "has to file a request with a small IT/BI team" and cite the Bank Director staffing findings.
6. **"GDPR and CCPA".** GDPR permits processors and transfers with safeguards; CCPA was not researched. Keep "reinforced by data-protection regulation", but do not imply either law forbids the use.
7. **Add a limitations paragraph** covering: no regulator requires on-prem; warehouse precondition (about 39% have one); data literacy; current accuracy gap; and the single-service-account RLS issue.
8. **Related work.** Add Oracle Select AI (private endpoint) and Metabase Metabot (self-hosted model, v64) as the closest deployed local comparables, alongside MATS.

### 8.3 Evaluation ideas this report suggests

- Determinism test from the prototype (stored SQL replay vs regeneration).
- Report execution accuracy next to the honest consequence: at 0.43, the system is only defensible with human review before an answer is shared, which is exactly what the promote tier provides.

---

## 9. Verify before citing

- SR 26-2 attachment (SR26-2a1.pdf) and OCC Bulletin 2026-13: confirm the generative-AI exclusion wording.
- PRA SS1/23 text and its AI/ML coverage.
- CBSL Direction No. 01 of 2026 primary PDF (data sovereignty condition); Sri Lanka PDPA No. 9 of 2022 cross-border transfer rules.
- EBA final non-ICT third-party guidelines; DORA critical-provider list date (18 vs 19 Nov 2025).
- CCPA / CPPA automated decision-making rules status.
- Kansas City Fed core-vendor figures against the brief PDF: https://www.kansascityfed.org/documents/10072/PaymentsSystemResearchBriefing24AlcazarBairdCronenwethHayashiIsaacson0327.pdf
- BriteCore "86% dissatisfied with analytics" (unverified; do not cite until read).
- Bloomberg Feb 2023 original on bank ChatGPT restrictions (only secondary coverage read).
- Tableau Agent on Tableau Server 2025.3; whether the REST API Connector works on Tableau Server.
- Whether self-managed ThoughtSpot Software includes Spotter.
- Which Metabase self-hosted editions include full Metabot with a self-hosted model.
- Whether Power BI custom visuals may call internal HTTP endpoints on Report Server.
- Conflicting Microsoft dates for push/streaming dataset retirement (2024 vs 2027).
- Exact Superset dataset/chart payloads for the installed version (`/swagger/v1`).
- Pricing for Snowflake Cortex Analyst, Databricks Genie, Amazon Quick Suite and Tableau+.
- Lloyds/NatWest sovereign-model coalition (aggregator source only).
- Cornerstone 2026 (49% banks deployed GenAI) vs Bank Director 2025 (52% none): always cite with the caveat.

### Gaps we could not fill

No current figure exists in these notes for: time to answer an ad hoc data request; BI backlog size or dashboard usage in financial services; who asks the questions; BI tool market share in community banks and credit unions; on-prem vs cloud warehouse split; a FinTech data-stack survey; recent credit-union data surveys; any independent accuracy benchmark of Copilot, Genie or Cortex Analyst on a public dataset. Do not fill these with estimates.
