# BI dashboard integration for an on-premise NL→SQL service (as of 18 Oct 2026)

Context: our FastAPI harness (`harness/app.py`) exposes `POST /query {query, db, mode}` → generated SQL, `columns`, rows, `steps`, `total_ms`; read-only DB connection; every handoff logged to `data/handoff.log.jsonl`. Question: how does a bank plug this into its BI dashboards without data leaving its network?

Labels: **[F]** = fact stated by the cited source · **[I]** = my inference · **[G]** = gap / not verified.

---

## 1. Power BI

### 1.1 Which Power BI is on-prem?
- [F] Power BI **Report Server (PBIRS)** is the on-prem product. Starting with SQL Server 2025, Microsoft consolidates all on-prem reporting under PBIRS; no new SSRS versions will ship; PBIRS is included with SQL Server 2025 Enterprise and Standard (for 2022 and earlier, only Enterprise + Software Assurance). SSRS 2022 is supported until 11 Jan 2033. https://learn.microsoft.com/sql/reporting-services/reporting-services-consolidation-faq?view=sql-server-ver17
- [F] PBIRS supports paginated (RDL) and interactive (PBIX) reports, row-level security, data modelling and custom visuals. Same source.
- [I] **Power BI Service is cloud (Microsoft Fabric).** Reaching an on-prem source from it goes through the on-premises data gateway, so query results (imported data or DirectQuery results) travel to Microsoft's cloud. That does not meet "no data may leave the bank's network". Treat Power BI Service as **out of scope** for the strict on-prem deployment; mention it only as "possible if the bank's AI-governance policy already approves Power BI Service".

### 1.2 Options and their on-prem status
| Mechanism | Works fully on-prem? | Notes |
|---|---|---|
| **DirectQuery to a SQL view** (pattern c) | **Yes (PBIRS)** | [F] PBIRS supports Live/DirectQuery for SQL Server, Oracle, PostgreSQL, Teradata, SAP HANA/BW, Azure SQL/Synapse. [F] Source-side RLS "should work" for DirectQuery to SQL Server, Oracle and Teradata if Kerberos is configured. https://learn.microsoft.com/power-bi/report-server/data-sources |
| **Import + scheduled refresh from a view** | Yes (PBIRS) | [F] SQL Server, Oracle, PostgreSQL all support scheduled refresh on PBIRS. Same source. |
| **Power Query Web connector → our REST API** (pattern d) | **Yes, with limits** | [F] PBIRS can refresh **only `Web.Contents`** web sources (not `Web.Page` / `Web.BrowserContents`). [F] PBIRS can't refresh reports whose URL is **built dynamically** from data, or a web source reached through an internet proxy. [F] PBIRS doesn't support OAuth for refresh. https://learn.microsoft.com/power-bi/report-server/data-sources , https://learn.microsoft.com/power-bi/report-server/scheduled-refresh . [F] `Web.Contents` becomes a POST when `Content` is set, but **"POST requests may only be made anonymously"**. https://learn.microsoft.com/powerquery-m/web-contents . [I] So for an authenticated refresh we need a **GET** endpoint with a fixed URL (e.g. `GET /answers/{id}.json` or `.csv`), not `POST /query`. |
| **Push / streaming datasets (REST)** | **No (cloud only) + deprecated** | [F] Real-time streaming is being retired (push, streaming, PubNub semantic models and streaming tiles). Microsoft docs disagree on dates: one page says new creation ended 31 Oct 2024 and existing models retire 31 Oct 2027; the main page says creation stays enabled until 31 Oct 2027. Microsoft points to Fabric Real-Time Intelligence. https://learn.microsoft.com/power-bi/connect-data/service-real-time-streaming , https://learn.microsoft.com/power-query/dataflows/load-dataflow-metadata-into-power-bi-dataset . Streaming dataflows are already retired. https://learn.microsoft.com/power-bi/transform-model/dataflows/dataflows-streaming . **Do not build on this.** |
| **Custom visual (.pbiviz)** calling our API | Partly | [F] Custom visuals work on PBIRS releases after May 2021. Power BI Desktop for Report Server tries to reach `pbivisuals.powerbi.com` and needs an environment-variable workaround when offline. https://learn.microsoft.com/power-bi/report-server/custom-visuals-troubleshoot . [F] Organizational-store visuals are not supported on PBIRS. https://learn.microsoft.com/power-bi/developer/visuals/power-bi-custom-visuals-organization . [G] I did not verify whether a custom visual's sandbox is allowed to make arbitrary HTTP calls to an internal API (Microsoft restricts web access for certified visuals). Treat a "chat visual inside a PBIX" as **unverified / high risk**. |
| **Embedding a report in our chat page** | **Yes** | [F] Any PBIRS report can be embedded in an iframe with `?rs:Embed=true`. PBIRS also has REST APIs and URL access. https://learn.microsoft.com/power-bi/report-server/developer-handbook-overview |
| Power BI Embedded / JS SDK, Copilot, Q&A | Cloud only | [I] These are Power BI Service features. [G] I didn't confirm whether PBIRS has Q&A. |

---

## 2. Tableau (Tableau Server = self-hosted)

- **Web Data Connector 3.0: deprecated, do not use.** [F] The `tableau/wdc3` repo was archived on 23 Mar 2026. Its README says WDC 3.0 "is deprecated and will not receive further updates" and "will be removed with the Tableau 26.3 release". It recommends the **REST API Connector** on Tableau Exchange (Tableau 2023.3+). https://github.com/tableau/wdc3 . [F] Older WDC 1.x/2.x were deprecated from 2023.1. https://kb.tableau.com/articles/en_US/Issue/web-data-connectors-deprecated-in-2023-1-release
- **REST API Connector.** [F] It is a JDBC REST driver that makes **HTTP GET** calls and reads JSON or CSV. It supports basic, bearer and OAuth auth and is **extract-only**. https://exchange.tableau.com/products/1111 . [G] Tableau Server support is not stated on the listing. [I] It needs a GET endpoint, the same as Power BI.
- **Hyper API** (push pattern). [F] You build `.hyper` extracts in Python/C++/Java and publish them to Tableau Server or Cloud through the REST API / Tableau Server Client. https://help.tableau.com/current/api/hyper_api/en-us , https://www.tableau.com/developer/tools/hyper-api . [I] This is a good on-prem fit for "save this answer as a dataset". Our service runs the SQL, writes a `.hyper` file and publishes it with `tableauserverclient`. All of this happens inside the bank.
- **TabPy / Analytics Extensions.** [F] TabPy runs Python through table calculations (`SCRIPT_*`). It is supported on Tableau Server 10.1+. https://www.tableau.com/developer/tools/python-integration-tabpy . [I] TabPy is designed for per-row calculations on data Tableau already holds. It is a poor fit for "question in, new result set out". [G] I didn't verify "table extensions" in official docs (blog sources only).
- **Embedding API v3.** [F] It uses the `<tableau-viz>` web component. Since 2021.4 it can authenticate with **connected apps**: the server signs a JWT and passes it as the `token` attribute. Tableau Server guides cover connected apps with direct trust or OAuth 2.0 trust. https://help.tableau.com/current/api/embedding_api/en-us/docs/embedding_api_auth.html . [I] This lets our chat page embed an existing Tableau Server view next to the NL answer.

---

## 3. Open-source on-prem BI

### Apache Superset (Apache-2.0)
- [F] It has a REST API for charts, including `POST /api/v1/chart/`, `GET/PUT/DELETE /api/v1/chart/{pk}` and a chart `/data/` endpoint. It also has a dashboard embedded-config endpoint `/api/v1/dashboard/{id_or_slug}/embedded`. https://superset.apache.org/docs/api . [F] A community example creates a chart by posting `slice_name`, `viz_type`, `datasource_id`, `datasource_type` and a JSON-string `params`, after login and a CSRF token from `/api/v1/security/csrf_token/`. Medium post (non-official): https://medium.com/@krprakruthiagri/apache-superset-dashboards-ui-vs-python-scripts-rest-api-fb9b99899ea6 . [G] I couldn't render the exact dataset-creation schema (`POST /api/v1/dataset/` with `sql` for a virtual dataset) from the official page. Check the instance's own Swagger at `/swagger/v1` before coding.
- **Embedding.** [F] It needs the `EMBEDDED_SUPERSET` feature flag and `@superset-ui/embedded-sdk`. The host's **server** fetches a guest token from `/api/v1/security/guest_token/` ("Do not call this endpoint from client-side code"). The token can carry **`rls` clauses** and expires after `GUEST_TOKEN_JWT_EXP_SECONDS` (default 5 minutes). Single charts can also be embedded via a permalink with `standalone=1`. https://superset.apache.org/user-docs/using-superset/embedding . [F] The SDK README says the requester needs the `can_grant_guest_token` permission. https://apache.googlesource.com/superset/+show/HEAD/superset-embedded-sdk/README.md
- **SQL Lab** gives analysts a governed place to paste and review generated SQL. [I] It is the natural "inspect / save as dataset" step.
- [F] There is no official Superset MCP or text-to-SQL feature in the search results. There are several community MCP servers (e.g. `mcp-superset` on PyPI). https://pypi.org/project/mcp-superset/ . [G] I didn't check the Superset 5.x/6.x release notes for built-in AI.

### Metabase (AGPL OSS edition + commercial editions)
- [F] The OSS edition is AGPL. The commercial licence adds a paid "Right to Embed". https://www.metabase.com/license/commercial , https://www.metabase.com/pricing.md
- [F] `POST /api/card` creates a question. For SQL, `dataset_query` = `{type: "native", native: {query: ...}, database: <id>}` plus `display` and `visualization_settings`. Authentication is by API key header. https://www.metabase.com/learn/administration/metabase-api
- [F] **Guest embedding** (the new name for static embedding, which is now deprecated) is available in OSS under Admin > Embedding. Your server signs a JWT with the embedding secret, and the token should carry `exp`. **Locked parameters** are applied server-side, but guest embeds **can't use row and column security**. OSS and Starter embeds show a Metabase banner. https://www.metabase.com/docs/latest/embedding/guest-embedding . [F] The embedded analytics SDK (including the AI chat component) is Pro/Enterprise only. https://www.metabase.com/docs/master/embedding/sdk/ai-chat
- **Metabot (a direct comparable).** [F] It went GA as a Cloud add-on in Metabase 58 (Jan 2026). Metabase 59 (Mar 2026) added single-shot prompt-based SQL in self-hosted instances. Metabase 60 (Apr 2026) added bring-your-own Anthropic key, self-hosted or cloud. Metabase 63 (Jul 2026) added OpenAI, Bedrock and Azure. **Metabase 64 (Oct 2026) added "an open model you host yourself with vLLM"**. https://www.metabase.com/releases-ai . [I] Metabase can now be fully local with a self-hosted model. That is the closest commercial/OSS analogue to our system, and it should be cited in the related work. [G] Which self-hosted editions include full Metabot (vs only SQL generation) is not stated.

### Grafana (AGPL-3.0)
- [F] The **Infinity** data source queries JSON/CSV/XML REST endpoints. **POST with a request body and headers** is supported; PUT/PATCH/DELETE need an admin opt-in. Versions before 3.4.1 have an SSRF CVE (CVE-2025-8341). https://grafana.com/docs/plugins/yesoreyeram-infinity-datasource/latest/advanced-features/url/ , https://grafana.com/blog/2025/09/04/whats-new-in-the-infinity-data-source-for-grafana-support-for-jq-parser-additional-http-methods-and-more
- [I] This is the **easiest pattern-(d) demo**. A Grafana panel POSTs `{query, db}` to our `/query` and renders the rows. But Grafana is built for time series and ops, and banks rarely use it as their business BI. Good for a demo, weak as the main story.

---

## 4. Existing NL→SQL tools and how they reach BI

| Tool | Status (Oct 2026) | Licence | BI integration |
|---|---|---|---|
| **Vanna** | [F] `vanna-ai/vanna` **archived 29 Mar 2026** (read-only). Its README describes Vanna 2.0: `<vanna-chat>` web component, Plotly charts, user-aware permissions, any LLM incl. Ollama; DBs incl. SQL Server, Oracle, Postgres, SQLite. https://github.com/vanna-ai/vanna | MIT | Its own chat UI + Plotly. **No BI-tool connector** in the README. |
| **WrenAI** | [F] Active. Wren Engine merged into the repo under `core/` on 7 May 2026. The old GenBI app was moved to the `legacy/v1` branch ("no new features or security fixes"). The OSS engine includes an MCP server and LangChain/Pydantic SDKs. "GenBI UI, dashboards, embedded and APIs" are **commercial**, and so is air-gapped deployment. https://github.com/Canner/WrenAI | Engine Apache-2.0 (repo also contains AGPL and CC-BY files) | It uses a semantic layer instead of BI connectors. Its dashboards are agent-built browser apps. |
| **Dataherald** | [F] The repo is not archived, but nothing on the page shows maintenance status. https://github.com/Dataherald/dataherald | Apache-2.0 | API-first NL→SQL engine. [G] Activity level not verified. |
| **Metabase Metabot** | See §3. Self-hosted model via vLLM since v64. | AGPL / commercial | Native: answers become Metabase questions and dashboards. |

[I] **Takeaway for the dissertation:** the ecosystem has split. One group is **BI-native assistants** (Metabot), which inherit the BI tool's permissions and save-as-question flow. The other is **standalone NL→SQL engines** (Vanna, Dataherald, Wren engine), which return SQL, rows and a chart spec and leave BI integration to the integrator. Our system belongs to the second group, so integration should follow BI-agnostic patterns.

---

## 5. Integration patterns compared

| Pattern | How | Pros | Cons / security |
|---|---|---|---|
| **(a) NL answer → "save as chart/tile"** | Chat UI → our service calls the BI API (Superset `POST /api/v1/chart/`, Metabase `POST /api/card`, Tableau Hyper publish) | Users explore in chat and **promote** good answers into the governed BI tool. Strong demo. | Needs a BI service account with write rights. Generated SQL must be reviewed before it is shared. The chart reruns the SQL under the BI tool's DB connection, not ours. |
| **(b) Chat panel embedded in a dashboard** | Our chat page and a BI iframe (PBIRS `?rs:Embed=true`, Superset guest token, Tableau connected-app JWT, Metabase guest JWT) side by side on one page | No BI-vendor changes. Works with every tool. | It is really "dashboard embedded in our page", not "chat inside the BI tool". A native in-report chat visual (Power BI custom visual) is unverified. |
| **(c) Generated SQL → governed view / dataset** | An analyst approves SQL → DBA creates a `VIEW` (or Superset virtual dataset / Metabase native question) → BI DirectQuery or refresh | **Best governance.** It reuses DB-level RLS and grants, follows normal change control, and the BI tool never calls the LLM. Works in PBIRS (DirectQuery to SQL Server/Oracle/Postgres). | Slow (human in the loop) and not interactive. Needs a promotion workflow. |
| **(d) BI calls the NL service as a data source** | Power Query `Web.Contents`, Tableau REST API Connector, Grafana Infinity → our endpoint | One query definition is pulled on a schedule. | **LLM output is non-deterministic, so the SQL can change between refreshes.** The dashboard number could change with the model, not the data. Needs a **frozen SQL id** (`GET /answers/{id}` replays stored SQL with no regeneration). PBIRS and Tableau REST connector need GET with a fixed URL. PBIRS POST is anonymous only. |

### Security points (all patterns)
- **Read-only identity and RLS reuse.** [I] The NL service should query as the **end user's DB identity**, or as a per-role read-only login, so the bank's existing DB grants and RLS apply. With one shared service account, every user sees everything that account sees, and RLS is bypassed. [F] PBIRS passes the user identity through for DirectQuery RLS on SQL Server, Oracle and Teradata only with Kerberos (source in §1.2). [F] Superset guest tokens and Metabase locked params apply filters that **the host app** decides. Metabase guest embeds can't use row and column security (sources in §3). So the host app (us) is responsible for mapping user → filter.
- **Statement guard.** [I] Keep the existing SELECT/WITH guard, read-only connection and timeout. Patterns (a) and (c) add a second gate: human review before SQL becomes shared.
- **Audit.** [I] `handoff.log.jsonl` already records trace id, SQL and result per attempt. Add user id and the BI artefact id (chart/card/view) so a dashboard number can be traced back to question → SQL → model version.
- **Secrets.** [F] Superset guest tokens and the Metabase embedding secret must stay server-side (sources in §3).
- **No egress.** [I] Every component in the recommended stack (PBIRS or Superset/Metabase, our service, local model) runs inside the bank. Note the PBIRS Desktop custom-visual internet lookup and Power BI Service gateway as egress traps.

---

## 6. Recommendation

**For a bank (on-prem):** use a **two-tier pattern**.
1. **Explore tier:** our chat UI (`/chat`) answers questions interactively. It is read-only, logged, and runs as the user's role.
2. **Promote tier (pattern c, with a+d as helpers):** an analyst clicks "save". The service stores the frozen SQL with an id, and either
   - creates a **governed DB view / BI dataset** that PBIRS reads via DirectQuery (Microsoft shops), or
   - creates a **Superset chart / Metabase question** through their API (OSS shops).
   Dashboards then run deterministic SQL under the bank's normal RLS and change control. The LLM is **never on the dashboard refresh path**.
3. **Display:** embed the existing dashboards next to the chat (PBIRS `?rs:Embed=true`, Superset guest token).

[I] Why: banks already govern views and BI datasets. Making the LLM a live data source (pattern d) puts a non-deterministic component into numbers that executives read. Avoid push/streaming datasets (deprecated, cloud-only) and WDC 3.0 (removed in Tableau 26.3).

---

## 7. Minimal prototype the team can build (about 1–2 days)

Stack: existing harness + **Apache Superset in Docker** (Apache-2.0, has REST + embedding, no licence friction) on the same machine, pointing at Chinook.

1. `POST /query` already returns `sql`, `columns` and rows. **Add `chart`**: a tiny rule-based suggestion (1 text column + 1 numeric → bar; date + numeric → line; else table) in the response. No LLM needed.
2. **Add `POST /answers`** to save `{question, sql, db, user, created}` and return an `id`. **Add `GET /answers/{id}.csv`**, which **replays the stored SQL** (no regeneration) through the existing read-only executor. This one endpoint covers pattern (d) for Power BI (`Web.Contents` GET), the Tableau REST API Connector, Grafana Infinity and Excel.
3. **Add `POST /answers/{id}/superset`**: the service logs into Superset, creates a virtual dataset from the stored SQL, then calls `POST /api/v1/chart/` with the suggested `viz_type`, and returns the chart URL. Check exact payloads against the instance's `/swagger/v1` first.
4. In `chat.html`: add a "Save as chart" button after a successful answer, plus an iframe of the created chart (`standalone=1`).
5. Evaluation hooks for the dissertation: log `answer_id` and `chart_id` in `handoff.log.jsonl`. Show that replaying `/answers/{id}.csv` returns identical rows across runs (determinism), and that generating again from the question may not.

Skipped: Power BI/Tableau live demos (licences, Windows/Kerberos setup). Describe them on paper using the GET CSV endpoint and a DirectQuery-to-view path. Per-user RLS: simulate with one read-only DB user per role if the panel asks.

---

## Gaps to close before citing
- Exact Superset dataset/chart JSON schema for the installed version (`/swagger/v1`).
- Whether Power BI custom visuals may call internal HTTP endpoints (WebAccess privilege) on PBIRS.
- Whether the Tableau REST API Connector is supported on Tableau Server (listing only mentions Desktop).
- Which conflicting Microsoft date is current for push/streaming dataset creation (2024 vs 2027 cut-off).
- Metabot feature coverage per self-hosted edition, and Dataherald maintenance activity.
