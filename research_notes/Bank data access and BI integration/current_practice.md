# How regional banks, mid-size insurers, credit unions and FinTechs get answers from internal data (as of Oct 2026)

Research notes for J26-DS-336. Compiled 18 Oct 2026 from web search; each figure carries its source URL and year. Where a figure was only seen in a secondary source (search excerpt, press coverage, vendor blog) it is marked **[secondary]**. Vendor-sponsored or vendor-published material is marked **[vendor]**. Nothing here was invented; where no number was found, the gap is listed at the end.

Evidence grades used below:
- **A**: independent or regulator source, primary document read.
- **B**: survey by an analyst/media firm, primary document read, but vendor-sponsored.
- **C**: secondary report of a survey (not read in the original), or old (pre-2023).
- **M**: vendor marketing / case study. Illustrative only, not evidence.

---

## 1. Facts (evidenced)

### 1.1 US community and regional banks: how data is held and accessed

**Bank Director 2025 Technology Survey** (grade B; sponsored by Jack Henry, a core vendor). 141 directors, CEOs, COOs, CFOs and senior technology executives of US banks under $100B assets; fielded June-July 2025; over half from $1B-$10B banks (asset mix: <$500M 24%, $500M-$1B 14%, $1B-$5B 39%, $5B-$10B 14%, >$10B 9%). Primary PDF read: https://www.bankdirector.com/wp-content/uploads/2025/09/2025TechReport-OpenVersion.pdf (summary: https://www.bankdirector.com/article/bank-directors-2025-technology-survey-banks-grapple-with-data-ai-maturity/)
- "How does your bank manage its data?" (select all; asked of executives and tech-background directors):
  - 56% keep data in the system or platform that generates or uses it
  - 56% rely on their **core provider to access their data**
  - 41% use **spreadsheets** to manage data used by business lines
  - 39% use a data lake or warehouse to combine data from different sources
  - 23% have **no formal data management strategy**
- 33% name "inability to use data effectively" as a top-3 technology concern (behind integrating new tech with existing systems 51% and rising tech costs 44%; "insufficient staff product or technology knowledge" 25%).
- 28% invested in data analysis platforms/capabilities in the past 18 months; **70% for banks over $10B** (sharp size gradient).
- Do you effectively use data analytics in...? Yes / No: regulatory compliance 50/41, enterprise risk 47/38, operations 38/53, marketing 36/57, HR 26/62. "Respondents from larger banks are much more likely to say they effectively use data analytics in all of these functions."
- Area most critically needing more in-house expertise: **data strategy and management 46%** (top answer), fraud 41%, customer experience 37%.
- Resource deficiencies (among the 33% who say tech is under-resourced): mid-level staffing "(programmers, developers, data scientists, etc)" 47%.
- AI posture: 66% have an AI acceptable-use policy; 62% experimenting in limited use cases; 41% updated vendor due diligence for AI risk; **15% have restricted/banned AI tools until further evaluation**; 14% no formal steps. 52% use generative AI in none of the listed functions. 32% upgraded/implemented enterprise-software AI tools (e.g. Microsoft Copilot, Google Gemini) in the last 18 months.
- Median 2025 tech budget $2.5M; median 14% of non-interest expense.
- Quote from sponsor (Jack Henry, J. Geis): relying on spreadsheets "introduces vulnerabilities around governance, data integrity, security and compliance". Opinion of a vendor, not a finding.

**Cornerstone Advisors / KlariVis "Data Execution Quality (EQ)" study** (grade B; commissioned by KlariVis, a bank BI vendor). 124 US banks and credit unions, $250M-$10B assets, surveyed August 2025, 70% of respondents SVP or above. Press release read: https://www.crnrstone.com/press-release/new-cornerstone-advisors-research-finds-community-banks-and-credit-unions-only-halfway-to-successfully-leveraging-their-data (18 Nov 2025)
- Average Data EQ score 241/500 ("little more than halfway"); credit unions 271, banks 211.
- One of the five scored areas is "effectiveness of data access and analysis capabilities" (sub-score not in the release).
- Weakest area sales and marketing (two-thirds below 50/100); best credit analysis (avg 51/100).
- $500M-$1B institutions scored lower than smaller peers.
- 35% have deployed chatbots; 25% experimenting with generative AI.
- The release does not mention ad hoc requests, spreadsheets, or core systems.

**Cornerstone "What's Going On in Banking 2026"** (grade B for the press release). 416 senior executives at US banks and credit unions $250M-$50B; released 29 Jan 2026. https://www.crnrstone.com/press-release/cornerstone-advisors-whats-going-on-in-banking-research-finds-ai-crypto-and-fraud-are-top-of-mind-for-banking-executives-in-2026
- 49% of banks and 59% of credit unions report having deployed generative AI; >80% plan to increase tech spending in 2026. The release gives no data-access or BI figures.
- Note the gap between this (49% deployed GenAI) and Bank Director (52% use GenAI in none of the listed functions); different samples, definitions and dates. Do not quote one without the other's caveat.

### 1.2 Dependence on core vendors (Fiserv, FIS, Jack Henry, etc.)

**Kansas City Fed, "Market Structure of Core Banking Services Providers"** (Payments System Research Briefing, March 2024; grade A for the existence of the brief, figures via search excerpt [secondary]). https://www.kansascityfed.org/research/payments-system-research-briefings/market-structure-of-core-banking-services-providers/
- Fiserv, FIS and Jack Henry together served over 70% of banks surveyed (2022) and nearly half of credit unions surveyed (2020).
- Fiserv 42% of banks / 31% of credit unions; Jack Henry 21% / 12%; FIS 9% / 3%. FIS leads among large banks, Jack Henry among small banks, Fiserv among small credit unions.
- 46% of community banks on a Big Three core were extremely or somewhat dissatisfied vs about 27% on smaller providers (2022 ABA data).
- The OCC's Nov 2025 request for information cites this brief (https://occ.treas.gov/news-issuances/federal-register/2025/90fr54882.pdf) [secondary].

**ABA core platform surveys** (grade C).
- 2022 survey (released Feb 2023): 47% of banks extremely or very satisfied with core provider, down from 59% in 2020; banks cited upgrade fees and **ability to access data** among problems. https://bankingjournal.aba.com/2023/02/aba-survey-fewer-than-half-of-banks-satisfied-with-core-provider/ [secondary]
- 2024 survey (article 2 May 2025): overall satisfaction 3.19 on a 1-5 scale, "low", modestly up. No data-access figure in the article. https://bankingjournal.aba.com/2025/05/aba-survey-banker-satisfaction-with-core-providers-remain-low/

Temenos and Finastra: no survey figures on their smaller-institution clients' data access were found (see Gaps).

### 1.3 Credit unions

- Cornerstone Data EQ (above): credit unions scored higher (271) than banks (211).
- Cornerstone 2026: 59% of credit unions report deployed GenAI.
- KC Fed: Big Three serve nearly half of credit unions (2020); market less concentrated than for banks.
- **Finalytics.ai Digital Maturity Index (2022, grade C, [vendor])**: credit unions $133M-$31B; only 12% had the capability of using internal and external data to drive outcomes, among the lowest-scoring areas. https://www.cubroadcast.com/episodes/2851-finalyticsai-survey-reveals-14-credit-unions-have-proper-approach-to-execute-digital-strategy
- **Filene Data Analytics Readiness survey (2021, grade C)**: top readiness lever was cultural ("create a truly data-driven decision-making environment"); percentages not found. https://www.filene.org/blog/findings-in-filenes-data-readiness-survey-help-credit-unions-find-value-in-their-data
- Shared/CUSO data warehouses exist as a product category, e.g. CU*Answers' warehouse on CU*BASE core data, priced at $1,000 setup + $10/GB/month [vendor]: https://www.cuanswers.com/wp-content/uploads/ai-datawarehouse_1page-sales.pdf ; Rise Analytics "Essential Analytics" bundle for credit unions starting their data journey (Oct 2025) [vendor]: https://www.cuinsight.com/press-release/rise-analytics-unveils-new-essential-analytics-offering-geared-towards-credit-unions-starting-their-data-journey/
- No current CUNA / America's Credit Unions / Callahan survey with BI-tool or data-warehouse adoption percentages was found.

### 1.4 Mid-size insurers

Evidence is thin and mostly vendor-sourced.
- **BriteCore 2025 P&C Core Systems Report** ([vendor], Oct 2025): 60 North American carriers, from under $100M to about $1B premium. Press release blocked (403); the frequently quoted "86% dissatisfied with analytics capabilities" appears only in a second vendor's blog citing it, so it is **unverified**. https://www.globenewswire.com/news-release/2025/10/29/3176360/0/en/BriteCore-Releases-2025-P-C-Core-Systems-Report-Highlighting-Industry-Shifts-Toward-Integration-Analytics-and-AI.html
- PwC (undated viewpoint, grade C): nearly 40% of mid-size insurers ($500M-$2B NWP) cite policy administration system replacement as a top-3 initiative for the next three years. https://www.pwc.com/en_US/us/financial-services/publications/viewpoints/assets/fs-viewpoint-fire-ready-aim-pas-transformation.pdf
- Reuters Events 2025 benchmarking (grade C, [secondary]): 86% of insurers invested in data analytics in the past 12 months. https://www.barchart.com/story/news/31990310/unlock-your-roi-new-benchmarking-report-reveals-keys-to-successful-tech-implementation-for-insurers
- Innovation Vista mid-market survey (2026 edition; grade C): insurers stronger on data/BI maturity (driven by regulatory and risk needs) than on AI. https://innovationvista.com/metrics/insur-analytics-maturity-survey

### 1.5 Growth-stage FinTechs

No survey of FinTech data stacks was found. Only vendor case studies [M]:
- Yellow Card (200+ staff fintech): four-person data team "had become a bottleneck for everyday questions"; moved to Metabase self-serve. https://www.metabase.com/case-studies/yellowcard
- Pipe (financing platform): moved from Looker to Preset (Apache Superset) over semantic-layer maintenance and per-seat cost. https://preset.io/blog/transitioning-from-looker-to-preset-to-enable-self-serve-analytics/
- Austin Capital Bank (community bank) adopted Snowflake, dbt, Fivetran and ThoughtSpot within 16 months, per Atlan. https://atlan.com/customers/austin-capital-bank-modern-data-stack/
- dbt Labs State of Analytics Engineering 2025 (grade C, [vendor], cross-industry): 459 practitioners, fielded Oct-Dec 2024; data quality the top challenge (56% per secondary source); 70% use AI in analytics development. https://www.getdbt.com/blog/state-of-analytics-engineering-2025-summary

### 1.6 Sri Lanka

- Rodrigo, Hettiarachchi and Kumarasinghe (2024), "An Exploration on Utilization of Business Analytics in Sri Lankan Banks", *Journal of Business and Technology* 8(1), 89-99, University of Kelaniya (grade A for what it claims; qualitative, n=5 professionals at private commercial banks). Banks use mainly Power BI and Tableau; most started analytics in the last 3-4 years, mostly in digital banking and cards; analytics "neither integrated fully with their core business nor achieved the expected value creation"; banks are "still in the early stages of business analytics maturity". https://jbt.sljol.info/articles/114
- Bank of Ceylon advertises a "Business Intelligence and Data Analytics Officer" role (shows in-house BI teams exist at the largest state bank). https://www.boc.lk/careers/business-intelligence-and-data-analytics-officer/details
- University of Moratuwa dissertation (year not confirmed): awareness of data warehousing high in commercial banks. https://dl.lib.uom.lk/bitstreams/fdab420d-38c3-48fb-b3eb-42e48809d27d/download

### 1.7 Cross-industry BI adoption and the analyst bottleneck (not bank-specific)

- **BARC / Eckerson "Strategies for Driving Adoption and Usage with BI and Analytics"** (survey late 2021, published Apr 2022; grade C for age; sponsored by BI vendors). 214 respondents. Employees actively using BI/analytics tools: **25% on average, minimal growth over seven years**. Natural-language query cited as a usage driver by only 14% (NA 20%, Europe 13%); self-service authoring 73%. https://barc.com/news/new-study-identifies-drivers-of-bi-and-analytics-adoption-in-companies-today/
- **Dresner** (interview, 2025; grade C): after ~16 years of Wisdom of Crowds research, average BI penetration among participating organisations is "still below 40%". https://www.datacamp.com/podcast/the-state-of-bi-in-2025
- Gartner, via IBM (date unclear, [secondary]): analytics/BI used by only 29% of employees on average. https://www.ibm.com/think/insights/business-intelligence-adoption
- Gartner (May 2024 abstract): business users are "underprepared to leverage" self-service analytics "even with GenAI-enabled natural language interactions, due to insufficient data literacy training". https://www.gartner.com/en/documents/5448363
- Gartner (24 Mar 2026 abstract): organisations "increasingly looking to move analytics use cases from dashboards to GenAI-fueled natural language query experiences"; emphasises semantic layers as a prerequisite. https://www.gartner.com/en/documents/7632029
- Gartner CDAO Agenda Survey (504 D&A leaders, Sept-Nov 2024; press release 20 Feb 2025): ~30% name inability to measure D&A/AI impact as top challenge; only 22% have defined business impact metrics for most use cases. https://www.gartner.com/en/newsroom/press-releases/2025-02-20-gartner-survey-finds-one-third-of-cdaos-cite-measuring-data-analytics-and-ai-impact-as-top-challenge
- Gartner 2023 CDAO survey via TechRepublic (grade C): poor data literacy cited by 22%; skills/staff shortages 38%. https://www.techrepublic.com/resource-library/downloads/gartner-data-analytics-summit-2023-generative-ai/
- TDWI (Sept 2025 webinar abstract, grade C): most organisations report fewer than half of business users actively engage with self-service tools. https://tdwi.org/webcasts/2025/09/adv-all-the-state-of-selfservice-analytics-results-from-tdwi-latest-research.aspx
- IDC for Alteryx (2018/2019; grade C, [vendor]): data workers spend ~44-50% of weekly time searching for, preparing or governing data. https://bigdatawire.com/2019/05/29/data-workers-failing-to-cope
- ThoughtSpot 2015 BI survey ([vendor], very old): backlog of several days for a simple report and three or more weeks for a complex one. https://www.thoughtspot.com/blog/top-5-takeaways-our-2015-bi-survey

### 1.8 Generative-AI governance in banks (relevant to the "why local" argument)

- 2023: JPMorgan restricted staff use of ChatGPT under "normal controls around third-party software"; Bank of America, Citi, Deutsche Bank, Goldman Sachs and Wells Fargo also reported as restricting it. https://www.americanbanker.com/articles/jpmorgan-restricts-staffs-use-of-ai-powered-chatgpt-bot
- 2025: 15% of US banks <$100B have restricted or banned AI tools pending evaluation; 41% updated vendor due diligence for AI risks (Bank Director, above).
- This supports the framing "generative-AI vendors are handled through internal AI-governance and vendor-risk policy", not a legal prohibition.

---

## 2. Typical stack (synthesis of the above, with confidence)

| Layer | Smaller banks / credit unions | Mid-size insurers | Growth-stage FinTech |
|---|---|---|---|
| System of record | Outsourced core (Fiserv/FIS/Jack Henry >70% of banks); data often reached *through the core provider* (56%) | Legacy policy admin + claims + billing systems; PAS replacement a top priority (PwC) | Own product database (cloud), payments/processor APIs |
| Integration | Data left in source systems (56%); warehouse/lake in 39%; CUSO or vendor warehouses for CUs | Data lake / warehouse projects (vendor case studies) | Cloud warehouse + ELT (Snowflake/BigQuery, dbt) per case studies |
| Reporting | Core-vendor canned reports, vendor BI add-ons (e.g. KlariVis), Power BI/Tableau; spreadsheets for business lines (41%) | Power BI etc.; regulatory reporting | Looker, Metabase, Superset/Preset |
| Who answers ad hoc questions | Small IT/finance staff; data talent is the top expertise gap (46%) | IT/actuarial/BI teams (no numbers found) | Small data team acting as bottleneck (Yellow Card case, [M]) |

Confidence: high for the US bank row (Bank Director primary data), low for insurers and FinTech (vendor case studies only). Specific tools such as SSRS, Qlik and on-prem SQL Server warehouses are plausible but no survey quantifying them in these segments was found.

---

## 3. Inferences (reasoned, not directly evidenced)

1. **The main gap at smaller institutions is people and integration, not dashboards.** Data strategy is the top in-house expertise gap (46%), mid-level data staff are a resource deficiency for 47% of those under-resourced, and 61% have no warehouse/lake. A tool that lets non-SQL staff query an existing database could address the people gap, but it presupposes a queryable, integrated database, which only ~39% have. This is a real adoption precondition for the appliance and should be stated as a limitation/assumption.
2. **Size gradient is steep.** 70% of >$10B banks invested in data platforms vs 28% overall. The target customer (regional bank / credit union without a large ML team) sits at the weak end, which supports the "no large GPU infra / ML team" premise but also means many lack the data foundation.
3. **Core-provider dependence matters for an on-prem appliance.** With 56% relying on the core vendor for data access, the appliance would often need to sit over a vendor-provided extract or reporting database rather than the core itself. Schema retrieval/pruning over vendor schemas (wide, abbreviated column names) is the realistic setting, which links to Agent 1's TPC-H abbreviated-column finding.
4. **Self-service BI has not solved the analyst bottleneck.** Cross-industry BI usage has sat at roughly a quarter to under 40% of employees for years (BARC 2022, Dresner 2025, Gartner via IBM), and Gartner explicitly ties this to data literacy, not tool availability. Natural-language query is the industry's proposed fix (Gartner 2026), but Gartner also says NL alone does not fix literacy. Honest claim for the dissertation: NL-to-SQL lowers the SQL barrier; it does not by itself guarantee correct interpretation by users.
5. **Generative AI is entering these institutions under governance controls.** Most have AI use policies and many restrict tools; a local system fits that governance posture. This is consistent with the project framing, but no source shows banks *choosing* local models over cloud for this reason; that remains an argument, not a finding.

---

## 4. Vendor marketing claims (do not cite as evidence)

- KlariVis: platform "unifies fragmented data" (in the Cornerstone release boilerplate).
- WNS (July 2025): large insurer cut reporting time 40% with a data lake + Power BI. https://www.wns.com/perspectives/case-studies/enterprise-data-lake-led-ecosystem-empowers-self-service-insurance-analytics
- "60-70% of dashboards go unused" attributed to Gartner on a vendor blog with no source; not verified. https://sds.apps.streamdata.com/blog/the-dashboard-delusion
- Perceptive Analytics: "74% of insurers still rely on legacy systems for core functions"; no methodology.
- Polygraf.ai: "~30% of financial firms ban or restrict employee GenAI"; survey not named.
- Metabase / Preset / Atlan / Snowflake customer stories (section 1.5).
- Commercial NL-to-data tools (Snowflake Cortex Analyst, Databricks Genie, ThoughtSpot): cite once as proof of demand, per project convention.

---

## 5. Gaps (not found; do not fill with guesses)

- **Time to answer an ad hoc data request** in banks/insurers: no current survey. Only a 2015 vendor survey (days to weeks) and university IT service targets. APQC has a cycle-time benchmark but values were not visible.
- **BI backlog size** and **dashboard usage rates** in financial services: no credible current figure.
- **Who asks the questions** (branch managers vs risk vs finance vs compliance): no survey quantifying requesters. Bank Director gives only per-function "effective use" self-ratings (compliance 50%, ERM 47%, operations 38%, marketing 36%, HR 26%).
- **BI tool market share** in community banks/credit unions (Power BI vs Tableau vs SSRS vs Qlik): not found.
- **On-prem vs cloud warehouse split** for these segments: not found.
- **Credit union** data surveys from America's Credit Unions (CUNA), Callahan or Filene newer than 2021: not found (may be paywalled).
- **Temenos / Finastra** smaller-client data access: nothing found.
- **Insurer** analytics surveys from Celent or Datos Insights (formerly Novarica): exist but paywalled; BriteCore 2025 report not readable.
- **FinTech** data-stack survey: none; only vendor case studies.
- **Sri Lanka**: only one small qualitative study (n=5) and job ads; no CBSL or industry survey on bank data access. Sri Lankan insurers and finance companies not covered.
- Reports to check directly if access is available: full Cornerstone Data EQ report (KlariVis), BARC "BI & Analytics Survey 26", Dresner Wisdom of Crowds BI Market Study 2025/2026 (financial-services cut), KC Fed brief PDF (https://www.kansascityfed.org/documents/10072/PaymentsSystemResearchBriefing24AlcazarBairdCronenwethHayashiIsaacson0327.pdf), ICBA/ABA regulatory burden surveys.
