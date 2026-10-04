# V.O.I.D. — Multi-Tiered Memory Architecture

## Memory Tiers

```
┌─────────────────────────────────────────────────────────┐
│                     V.O.I.D. MEMORY                     │
├─────────────────────────────────────────────────────────┤
│ 1. WORKING MEMORY    • In-memory conversation & task    │
│ 2. EPISODIC MEMORY   • Interaction log & tool history   │
│ 3. SEMANTIC MEMORY   • Facts & world knowledge (Vectors)│
│ 4. PREFERENCE MEMORY • User style, name & formatting    │
│ 5. PROJECT MEMORY    • Codebase architecture & decisions│
│ 6. PROCEDURAL MEMORY • Multi-step execution workflows   │
└─────────────────────────────────────────────────────────┘
```

---

## Schema & Storage
Stored locally in `void_memory/void_memory.db` (SQLite) with embeddings generated via `all-MiniLM-L6-v2`:
```sql
CREATE TABLE memory_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL,
    date_str TEXT,
    tier TEXT,
    category TEXT,
    text TEXT UNIQUE,
    embedding BLOB,
    importance REAL,
    access_count INTEGER DEFAULT 0,
    last_accessed REAL
);
```

---

## Retrieval & Ranking
Relevance score is computed via hybrid ranking:
$$\text{Score} = 0.70 \times \text{CosineSimilarity}(\vec{q}, \vec{m}) + 0.30 \times \text{Importance}$$

---

## Explicit Deletion ("Forget That")
When the user says:
> *"VOID, forget that."* or *"VOID, delete my memory about X"*

`VoidMemory.forget_memory(query)` immediately purges matching rows from SQLite, providing verifiable privacy and user agency.
