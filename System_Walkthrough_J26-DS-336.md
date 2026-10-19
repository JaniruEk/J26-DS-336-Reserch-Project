# How the J26-DS-336 system works — a walkthrough for the panel

*As of 18 October 2026*

## The setup

A bank manager types a question in plain English; the system turns it into a database query (SQL), runs it and shows the answer. Everything runs on the bank's own mid-range hardware, so no question or data is ever sent to an outside AI company.

This walkthrough follows one real question from start to finish. It uses the Chinook test database (a music store with 11 tables and about 65 columns: customers, invoices, tracks, albums, employees and more).

> **Example question:** "Which customers have spent more than $40 in total?"

The question passes through three agents, one after another, each owned by a team member. Two more pieces of work happen once, beforehand, to build the AI model the agents use.

## Step 1: Agent 1 picks only the parts of the database the question needs (Ekanayake)

The AI model that writes SQL is small. Shown all 11 tables and 65 columns, it gets confused, slows down and invents names, so Agent 1 first selects only the relevant parts. Think of handing a junior employee the two folders they need, not the whole filing cabinet.

**Input:** the question and a live, read-only connection to the database.

**What happens inside:**

1. **Find the starting table.** It compares the meaning of the question with each table's description; "customers… spent" points to the Customer and Invoice tables.
2. **Follow the links.** Tables are joined by keys (Invoice holds a CustomerId pointing to Customer), so it pulls in the tables needed to connect them.
3. **Prune the columns (the research contribution).** Inside each table it keeps only the relevant columns. Customer has 13 columns (phone, fax, address, email…); this question needs only CustomerId, FirstName and LastName, plus CustomerId and Total from Invoice.

It also labels the question's difficulty: simple, single-join, multi-join or aggregation. This one is **aggregation**, because it adds up totals.

**Output (handed to Agent 3):**

```
Complexity: aggregation
Schema (pruned):
  Customer (CustomerId, FirstName, LastName)
  Invoice  (InvoiceId, CustomerId, Total)
Size: ~145 tokens instead of ~171 for the unpruned schema (about 16% smaller)
```

**Research question:** does giving the AI only the relevant columns, rather than whole tables, make it faster and more accurate? So far: about 16% less text with no loss of accuracy (0.43 vs 0.41 execution accuracy), but not yet a statistically significant gain with the current stand-in model.

## Step 2: Agent 3 writes the SQL (Thathsarani)

Agent 3 turns the English question into a correct SQL query. Small AI models are weakest on hard questions, especially those that combine several tables or calculate totals.

**Input (from Agent 1):** the question, the pruned schema and the difficulty label (aggregation).

**What happens inside:** a small AI model, trained on thousands of question-to-SQL examples, writes the query. The research is about how to train it:

- **Standard method (LoRA):** one set of extra training weights shared by every kind of question.
- **Specialist method (HydraLoRA):** a separate specialist "head" for each difficulty level. Agent 1's label chooses the head, so this question goes to the aggregation specialist.

Think of one general doctor versus a clinic of specialists, where a receptionist (Agent 1's label) sends each patient to the right one.

**Output (handed to Agent 4):**

```sql
SELECT c.FirstName, c.LastName, SUM(i.Total) AS TotalSpent
FROM Customer c JOIN Invoice i ON c.CustomerId = i.CustomerId
GROUP BY c.CustomerId
HAVING SUM(i.Total) > 40;
```

**Research question:** does a specialist head per difficulty beat one general set of weights, without adding many more trainable parameters? So far: standard LoRA raised execution accuracy from 0.41 (untrained) to 0.55; the HydraLoRA comparison is next.

## Step 3: Agent 4 runs the SQL safely and returns the answer (Karunanayake)

Agent 4 runs the query **read-only**, so it can never change or delete bank data. If the query fails, it works out why and sends a hint back to Agent 3 to try again, at most 3 times.

**Input:** the SQL from Agent 3.

**What happens inside:**

1. A safety check confirms it is a single, read-only query.
2. The query runs on the database.
3. On an error such as "no such column", Agent 4 diagnoses it and sends a hint back to Agent 3, which writes a corrected query.

**Output (to the user):** the answer table, plus the SQL so an analyst can check it.

```
FirstName   LastName    TotalSpent
Helena      Holý        49.62
Richard     Cunningham  47.62
...
```

Inushki's research is the other half of Agent 4: shrinking the AI model so it runs on mid-range hardware (next section).

## Where the AI model comes from (built once, before going live)

The model used in Step 2 is built once, in advance, in three stages, much like manufacturing an engine before the car is driven. Each stage hands its result to the next.

| Stage | Owner | Input | What happens | Output (handed to) | Research question |
| --- | --- | --- | --- | --- | --- |
| 1. Build a better small model | Wathsala (Agent 2) | A large "teacher" model (~7 billion parameters) and a few thousand practice questions | The teacher answers the questions; a small "student" model learns to copy its answers (**knowledge distillation**), like a professor's worked solutions training a student | Two small models of the same size, one taught, one ordinary (to Thathsarani) | Does a small model taught by a big teacher reason better than an ordinary small model of the same size? |
| 2. Train it for SQL | Thathsarani (Agent 3) | Those two small models, plus questions labelled by difficulty with Agent 1's classifier | Fine-tunes them for SQL, comparing standard LoRA with the specialist-head HydraLoRA | Her best model and her second-best (to Inushki) | Does a specialist head per difficulty beat one general set of weights? |
| 3. Shrink it to fit | Karunanayake (Agent 4) | The best and second-best trained models | Compresses the model by storing its numbers with fewer bits, either during training (QAT) or after it (PTQ), like compressing a photo without losing the fine detail | The final compressed model that runs live in Step 2 | Which compression method keeps SQL reasoning best, and does the answer hold for the second-best model too? |

Careless compression mostly loses the fine detail behind sums and averages, which is exactly what aggregation questions need.

## The whole picture

The top band runs once to produce the model; the bottom band runs for every question, and the compressed model from the top band is what Agent 3 uses.

```
BUILT ONCE, BEFORE GOING LIVE
  [Wathsala · Agent 2]  ──►  [Thathsarani · Agent 3]  ──►  [Karunanayake · Agent 4]
   big teacher trains         trains it to write SQL         compresses it to fit
   a small student model      (LoRA vs HydraLoRA)            mid-range hardware
                                                                     │
                                                    compressed model │ runs inside Agent 3
                                                                     ▼
EVERY QUESTION (live, a few seconds)
  [Question] ──► [1 · Ekanayake] ──► [3 · Thathsarani] ──► [4 · Karunanayake] ──► [Answer]
   in plain       picks needed        writes the SQL        runs it read-only      table
   English        tables & columns    (specialist head)     and returns rows       + the SQL
                  + difficulty label         ▲                     │
                                             └─────────────────────┘
                                         error → hint, try again (max 3)
```

A small coordinator program, the harness, passes the work between agents and records every handoff, so anyone can see exactly what each agent received and produced. The chat page shows this as the "Pipeline trace".

## The one thing to tell the panel

Each of the four members runs one controlled experiment on one step: retrieval, model building, training method and compression. Each changes one thing and measures the effect.

The research contribution is these four measured findings, not the app itself. The combined system only shows that the four winning choices work together, and a finding that a technique did not help is still a valid result.
