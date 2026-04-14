# Day 7 Supplementary — Big Data Internals
## Hadoop · HDFS · MapReduce · Spark · Kafka · CDC · Airflow

> **How to use this document.** This is an architecture-first reference, not a getting-started guide. Each section explains *why* a system is designed the way it is before explaining *what* it does. Al-Noor Bank scenarios are used throughout to keep the content grounded in the Saudi banking context you are working in.

---

## 1. What "Big Data" Actually Means Architecturally

The 5 Vs are a useful shorthand, but they are not the reason big data infrastructure exists. The real reason is that **a single machine hit a ceiling** — in storage, in compute, or in both — and the solution was to distribute the problem across many machines and coordinate them.

Every tool covered in this document is an answer to a specific version of that ceiling:

| Ceiling hit | Answer |
|---|---|
| A file is too large for one disk | HDFS — split the file across many disks, replicate for fault tolerance |
| A computation is too slow on one CPU | MapReduce / Spark — split the work, run in parallel, merge results |
| Events arrive faster than batch jobs can absorb | Kafka — durable, ordered event log that decouples producers from consumers |
| Pipelines need coordination, retries, and scheduling | Airflow — DAG-based orchestrator that treats pipelines as code |

Understanding *which ceiling each tool addresses* is more useful than memorising feature lists.

---

## 2. Apache Hadoop

### 2.1 Why Hadoop Existed

Before Hadoop (pre-2006), processing a dataset that did not fit on one machine required either buying a very expensive specialised server or writing custom distributed code from scratch. Google published two papers — the GFS paper (2003) and the MapReduce paper (2004) — describing how they solved this internally. Doug Cutting and Mike Cafarella built the open-source implementation, naming it after a toy elephant.

Hadoop solved three problems simultaneously:

1. **Where do you store data that is too large for one machine?** → HDFS
2. **How do you run computation across that data without moving it all to one place?** → MapReduce
3. **How do you manage the cluster resources?** → YARN (Yet Another Resource Negotiator)

### 2.2 The Hadoop Cluster Model

A Hadoop cluster runs on commodity hardware — standard servers rather than specialist storage arrays. This was the architectural bet: instead of buying one very reliable expensive machine, buy many cheap machines and build reliability into the software layer.

The cluster has two node types:

**NameNode (master)** — holds the file system namespace. It knows where every block of every file lives, but it does not store the data itself. It is the directory, not the filing cabinet.

**DataNodes (workers)** — store the actual data blocks and execute the computations. A production cluster typically has tens to hundreds of DataNodes.

```
                    ┌─────────────┐
                    │  NameNode   │  ← metadata only: "file X is blocks 1,2,3 on DN-4,DN-7,DN-2"
                    └──────┬──────┘
                           │ heartbeat + block reports
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │DataNode 1│    │DataNode 2│    │DataNode 3│
    │ Block A  │    │ Block A  │    │ Block B  │   ← replication factor = 3
    │ Block C  │    │ Block B  │    │ Block C  │
    └──────────┘    └──────────┘    └──────────┘
```

### 2.3 HDFS — Hadoop Distributed File System

#### How a file gets stored

When you write a 1 GB file to HDFS:

1. The client asks the NameNode where to write.
2. The NameNode assigns a list of DataNodes for each block (default block size: 128 MB → 8 blocks for 1 GB).
3. The client writes block 1 to DataNode A. DataNode A **pipelines** the write to DataNode B, which pipelines to DataNode C. This is the replication pipeline.
4. Each DataNode sends an acknowledgement back up the pipeline.
5. The client proceeds to block 2 only after all replicas of block 1 are confirmed.
6. Once all blocks are written, the client tells the NameNode to commit the file metadata.

The NameNode never touches the data itself. It only updates its metadata: "file `/data/transactions/2024-01-15.csv` = blocks [101, 102, 103, 104, 105, 106, 107, 108], each replicated on three DataNodes."

#### Replication and fault tolerance

With a replication factor of 3, HDFS can survive the loss of 2 DataNodes without losing data. The NameNode detects a dead DataNode via missed heartbeats (default: 10 minutes) and instructs surviving DataNodes to re-replicate any under-replicated blocks.

Rack awareness: HDFS places replicas across different physical racks. For a replication factor of 3: one replica on the local rack, two on a remote rack. This protects against a full rack switch failure.

#### What HDFS is not good at

- **Small files** — each file requires a metadata entry in the NameNode's memory. One million small files consumes the same NameNode memory as one million large files. The data volume is irrelevant; the file count is what matters.
- **Random writes** — HDFS is append-only by design. You cannot update a byte in the middle of a block. This is intentional: it eliminates the locking complexity of concurrent random writes.
- **Low-latency reads** — HDFS optimises for throughput, not latency. A single 1 GB sequential read is fast. Reading the same 100 bytes repeatedly from many small files is slow.

In the Al-Noor context: HDFS (or its cloud equivalents, S3/ADLS) stores raw CBS extract dumps, SWIFT message archives, and historical transaction logs that are written once and read in bulk during DWH ELT runs. It is not used for anything requiring sub-second random access — that is Redis or PostgreSQL's job.

---

## 3. MapReduce

### 3.1 The Core Idea

MapReduce is a programming model, not just a tool. It takes a problem that looks like this:

> "I have 1.3 billion transaction rows spread across 200 DataNodes. I want to count the total transaction value per branch, per month."

And breaks it into two phases that can run in parallel:

**Map phase** — each worker reads its local data blocks and emits `(key, value)` pairs. No worker talks to any other worker during this phase.

**Reduce phase** — all values for the same key are collected onto one worker, which aggregates them.

### 3.2 The Execution Flow in Detail

Using the Al-Noor example — sum transaction amounts by branch:

**Step 1 — Input Splits**

The framework divides the input data into splits (typically one per HDFS block). Each split is assigned to a Map task. With 1.3 billion rows across 200 DataNodes, there might be 1,600 Map tasks running in parallel.

**Step 2 — Map**

Each Map task reads its input split and runs your map function. For each row, the map function emits a key-value pair:

```
Input row:  txn_id=9001, branch=RUH-03, amount=15000, date=2024-01-15
Map output: ("RUH-03|2024-01", 15000)
```

**Step 3 — Shuffle and Sort**

This is the most expensive phase, and it happens automatically. The framework:
- Sorts all map outputs by key
- Transfers all values for the same key to the same Reduce task (this involves network transfer — the "shuffle")
- Sorts again by key on the reducer side

The shuffle is why MapReduce is slow for iterative algorithms: every iteration requires a full shuffle across the network.

**Step 4 — Reduce**

Each Reduce task receives all values for a group of keys and runs your reduce function:

```
Input:  ("RUH-03|2024-01", [15000, 8200, 42000, 3100, ...])
Output: ("RUH-03|2024-01", 2,847,350,000)
```

**Step 5 — Output**

Results are written back to HDFS.

```
Input Data (HDFS)
      │
      ▼
 ┌─────────────────────────────────────────────────────────┐
 │  MAP PHASE  (parallel, one task per input split)        │
 │  task 1: reads blocks on DN-1  → emits (k,v) pairs     │
 │  task 2: reads blocks on DN-2  → emits (k,v) pairs     │
 │  task N: reads blocks on DN-N  → emits (k,v) pairs     │
 └────────────────────────┬────────────────────────────────┘
                          │  SHUFFLE & SORT
                          │  (network transfer, sort by key)
                          ▼
 ┌─────────────────────────────────────────────────────────┐
 │  REDUCE PHASE  (parallel, one task per key group)       │
 │  reducer A: all values for keys A–M → aggregates        │
 │  reducer B: all values for keys N–Z → aggregates        │
 └────────────────────────┬────────────────────────────────┘
                          │
                          ▼
                   Output (HDFS)
```

### 3.3 Why MapReduce Was Eventually Superseded

MapReduce writes intermediate results to disk between every Map and Reduce phase. For a two-stage job this is acceptable. For an iterative algorithm — machine learning, graph traversal, multi-step SQL — you pay disk I/O at every step. A 10-iteration ML training job in MapReduce does 20 full HDFS read/write cycles. Spark replaced this with in-memory processing.

MapReduce is still running in production in many banks with legacy Hadoop clusters. Understanding it is necessary for reading old pipeline code and diagnosing legacy jobs.

---

## 4. Apache Spark

### 4.1 The Architectural Shift: Memory over Disk

Spark's foundational insight was: **intermediate data does not need to touch disk**. Keep it in the JVM heap across the cluster. For iterative workloads, this produces order-of-magnitude speedups. For single-pass ETL the difference is smaller, but Spark's richer API — DataFrames, SQL, streaming — made it the dominant replacement for MapReduce regardless.

### 4.2 Spark Architecture

A Spark application has three components:

**Driver** — the process running your main program. It creates the SparkContext, builds the execution plan, and coordinates with the cluster manager. There is exactly one Driver per application.

**Cluster Manager** — allocates resources. This can be YARN (if running on Hadoop), Kubernetes, Mesos, or Spark Standalone. The cluster manager does not know anything about Spark internals — it just assigns CPU and memory.

**Executors** — JVM processes running on worker nodes that actually execute the tasks. Each executor has a fixed number of CPU cores and a fixed memory allocation for the lifetime of the application.

```
┌─────────────────────────────────────────────────────────────┐
│                      SPARK APPLICATION                      │
│                                                             │
│   ┌──────────┐      ┌────────────────┐                     │
│   │  Driver  │◄────►│ Cluster Manager│                     │
│   │(your code│      │ (YARN / K8s)   │                     │
│   │+ planner)│      └────────────────┘                     │
│   └────┬─────┘                                             │
│        │ task assignment                                    │
│        ▼                                                    │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│  │Executor 1│   │Executor 2│   │Executor 3│               │
│  │core0 core1   │core0 core1   │core0 core1               │
│  │[task][task]  │[task][task]  │[task][task]              │
│  └──────────┘   └──────────┘   └──────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 RDDs, DataFrames, and the Catalyst Optimizer

**RDD (Resilient Distributed Dataset)** is Spark's original abstraction — a distributed collection of objects across the cluster. RDDs support two operation types:

- **Transformations** (lazy) — define what to do: `filter()`, `map()`, `join()`. Nothing executes.
- **Actions** (eager) — trigger execution: `count()`, `collect()`, `write()`.

This laziness is deliberate. Spark collects all transformations into a **Directed Acyclic Graph (DAG)** before executing anything. The Catalyst optimizer then rewrites that DAG to eliminate unnecessary work — pushing filters earlier, reordering joins, choosing broadcast joins for small tables.

**DataFrames and Datasets** are the modern API. They sit on top of RDDs and give Spark a schema, enabling Catalyst to apply SQL-style optimisations. When you write Spark SQL or use the DataFrame API, you are always going through Catalyst. When you write low-level RDD transformations, you bypass it.

### 4.4 Lazy Evaluation and the DAG — A Concrete Example

```python
# This block defines a DAG. Nothing executes yet.
df = spark.read.parquet("s3://al-noor-datalake/raw/transactions/")   # step 1
df_filtered = df.filter(df.txn_date == "2024-01-15")                  # step 2
df_joined   = df_filtered.join(dim_branch, "branch_id")               # step 3
df_agg      = df_joined.groupBy("branch_name").sum("amount")           # step 4

# This triggers execution. Catalyst optimises steps 1-4 before running anything.
df_agg.write.parquet("s3://al-noor-datalake/curated/branch_daily/")  # action
```

Catalyst might reorder this to push the date filter into the Parquet reader (predicate pushdown), avoiding the read of irrelevant partitions entirely. You wrote 4 steps; Catalyst may execute 2.

### 4.5 Partitions and Parallelism

A Spark DataFrame is divided into partitions. Each partition is processed by one task on one executor core. The level of parallelism equals the number of partitions.

Rules of thumb:
- Target 2–4 partitions per CPU core in your cluster
- Each partition should be 100–200 MB of data
- Too few partitions → cores sit idle. Too many → scheduling overhead dominates.

`repartition(n)` triggers a full shuffle to redistribute data evenly. `coalesce(n)` reduces partition count without a full shuffle (useful before writing output).

### 4.6 Spark vs. MapReduce — The Key Difference

| | MapReduce | Spark |
|---|---|---|
| Intermediate data | Written to HDFS | Kept in memory (spills to disk only if needed) |
| API | Java only (originally) | Python, Scala, Java, R, SQL |
| Iterative workloads | One full HDFS cycle per iteration | Cache dataset in memory, iterate without I/O |
| Streaming | Not native | Spark Structured Streaming (micro-batch or continuous) |
| Optimiser | None | Catalyst (cost-based and rule-based) |

In the Al-Noor platform, Spark runs the nightly ELT job that reads yesterday's ODS transactions from PostgreSQL, joins them against dimension tables in Delta Lake, and writes `FACT_TRANSACTION` back to Delta Lake — a single-pass job where Spark's real advantage is the DataFrame API and Delta ACID guarantees rather than pure speed.

---

## 5. Apache Kafka

### 5.1 The Problem Kafka Solves

Before event streaming platforms, service integration looked like this: System A writes to a database table; System B polls that table every 5 minutes; System C does the same with a different polling interval; System D needs the data in a different format entirely. You end up with a mesh of point-to-point integrations, each one a custom contract, each one a failure point.

Kafka replaces this with a **publish-subscribe event log**. System A publishes an event once. Every downstream system subscribes independently and reads at its own pace. Adding a new consumer does not require changing System A at all.

### 5.2 Kafka's Internal Architecture

Kafka is a **distributed, durable, append-only log**. Those three words are the architecture:

- **Distributed** — spread across a cluster of broker nodes
- **Durable** — events are written to disk and replicated before being acknowledged
- **Append-only** — events are never modified or deleted (until retention expires)

#### Brokers and the Cluster

A Kafka cluster consists of multiple **broker** processes, each running on a separate server. Brokers are peers — there is no single master broker (though one broker acts as the **Controller** for administrative tasks like partition leadership elections).

Historically, Kafka relied on **ZooKeeper** for cluster coordination and metadata storage. From Kafka 2.8 onwards, **KRaft mode** replaces ZooKeeper with a built-in Raft-based metadata log, eliminating the operational complexity of running a separate ZooKeeper ensemble. New deployments in 2024+ should use KRaft.

```
┌──────────────────────────────────────────────────────┐
│                   KAFKA CLUSTER                      │
│                                                      │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│   │ Broker 1 │   │ Broker 2 │   │ Broker 3 │        │
│   │(Controller   │          │   │          │        │
│   └──────────┘   └──────────┘   └──────────┘        │
│                                                      │
│   Topics and their partitions are distributed        │
│   across all brokers. Each partition has one         │
│   leader broker and N-1 follower brokers.            │
└──────────────────────────────────────────────────────┘
```

### 5.3 Topics and Partitions

A **Topic** is a named, ordered, persistent log. Think of it as a category of events: `transactions.posted`, `customers.updated`, `kyc.events`.

A topic is divided into **Partitions**. Each partition is an independent ordered log stored on disk. Partitions are the unit of parallelism in Kafka.

```
Topic: transactions.posted
  Partition 0:  [offset 0] [offset 1] [offset 2] [offset 3] ...→ (append-only)
  Partition 1:  [offset 0] [offset 1] [offset 2] ...→
  Partition 2:  [offset 0] [offset 1] ...→
  ...
  Partition 23: [offset 0] ...→
```

**Why partition?**
- A single partition can only be written by one thread at a time. More partitions → higher throughput.
- Each partition is assigned to one broker as its **leader**. Work is spread across the cluster.
- Each partition is consumed by at most one consumer per consumer group. More partitions → more consumer parallelism.

**Partition assignment** — when a producer sends a message:
- If a key is provided (e.g., `account_id`): the partition is determined by `hash(key) % num_partitions`. All events with the same key land on the same partition, preserving order per key.
- If no key: round-robin across partitions.

In the Al-Noor platform, `transactions.posted` is partitioned by `account_id`. This guarantees that all events for account A12345 are in the same partition and are processed in the order they occurred.

**Replication** — each partition has one leader and `replication_factor - 1` followers. Followers replicate from the leader. If the leader broker fails, the controller elects a new leader from the in-sync replicas (ISR).

```
Partition 0 of transactions.posted:
  Leader:   Broker 1  ← producers write here, consumers read here
  Follower: Broker 2  ← replicates from Broker 1
  Follower: Broker 3  ← replicates from Broker 1
```

### 5.4 Producers

A producer is any application that writes events to a Kafka topic. The producer is responsible for:

**Serialisation** — converting the message to bytes (JSON, Avro, Protobuf).

**Partitioning** — deciding which partition to write to (via the key hash or custom partitioner).

**Batching** — accumulating messages in an in-memory buffer before sending, to improve throughput. Controlled by `batch.size` (max bytes) and `linger.ms` (max wait time).

**Acknowledgement** — the `acks` setting controls durability guarantees:

| `acks` setting | Meaning | Risk |
|---|---|---|
| `0` | Fire and forget. No acknowledgement. | Message loss on broker failure |
| `1` | Leader acknowledges. | Message loss if leader fails before follower replication |
| `all` (or `-1`) | All in-sync replicas acknowledge. | No loss; highest latency |

For banking transactions, `acks=all` is non-negotiable. SAMA DMF requires that every submitted transaction is recoverable.

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers='kafka.al-noor.internal:9092',
    key_serializer=lambda k: k.encode('utf-8'),
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    acks='all',                   # wait for all ISR replicas
    retries=5,                    # retry on transient failure
    max_in_flight_requests_per_connection=1  # preserve ordering on retry
)

producer.send(
    topic='transactions.posted',
    key='ACC-00123456',           # partition key — routes to same partition
    value={
        'txn_id': 'TXN-2024-001',
        'account_id': 'ACC-00123456',
        'amount': 15000.00,
        'currency': 'SAR',
        'txn_type': 'MURABAHA_PAYMENT',
        'timestamp': '2024-01-15T14:32:00Z'
    }
)
producer.flush()
```

### 5.5 Consumers and Consumer Groups

A **consumer** reads events from one or more topic partitions. It tracks its position using the **offset** — the sequential ID of the last message it processed.

A **consumer group** is a set of consumers that collectively process a topic. Kafka assigns each partition to exactly one consumer within a group. This is the parallel processing model: more consumers in a group → more partitions processed simultaneously, up to the number of partitions.

```
Topic: transactions.posted (24 partitions)
Consumer Group: dwh-etl-group (6 consumers)

Consumer 1 → Partitions 0, 1, 2, 3
Consumer 2 → Partitions 4, 5, 6, 7
Consumer 3 → Partitions 8, 9, 10, 11
Consumer 4 → Partitions 12, 13, 14, 15
Consumer 5 → Partitions 16, 17, 18, 19
Consumer 6 → Partitions 20, 21, 22, 23
```

A different consumer group — `aml-engine-group` — gets all the same events independently. Adding an AML consumer group requires zero changes to the producer or to the DWH consumer group.

**Offset management** — consumers commit their offsets to a special Kafka topic (`__consumer_offsets`). On restart, the consumer resumes from the last committed offset. This gives exactly-once semantics when combined with idempotent consumers (i.e., processing the same message twice produces the same result).

**Rebalancing** — when consumers join or leave a group, Kafka triggers a **rebalance**: partitions are redistributed across the current members. During a rebalance, consumption pauses. This is the main operational pain point for consumer groups — minimise unnecessary consumer restarts.

### 5.6 Retention and Log Compaction

Kafka retains events based on configuration, not consumption. A consumer falling behind does not cause messages to be deleted.

**Time-based retention** (`retention.ms`) — delete segments older than N milliseconds.

```
transactions.posted → 7 days   (recent events for operational use)
customers.updated   → 30 days  (longer for ODS reconciliation)
```

**Log compaction** (`cleanup.policy=compact`) — retain only the **most recent event per key**. Useful for topics where each key represents an entity and you only care about its current state (e.g., customer profile updates). Older events for the same key are deleted during compaction.

In the Al-Noor platform:
- `transactions.posted` uses `delete` policy — every individual transaction event is significant and must be retained for 7 days in Kafka, then archived to Data Lake for 10 years.
- `customers.updated` uses `compact` policy — you care about the current state of each customer record, not every intermediate update.

### 5.7 Kafka Connect and the Connector Ecosystem

Running custom consumer code for every integration is operationally expensive. **Kafka Connect** is a framework for running pre-built source and sink connectors without writing consumer code.

- **Source connectors** — pull data from external systems into Kafka topics (e.g., Debezium reading PostgreSQL WAL)
- **Sink connectors** — push data from Kafka topics into external systems (e.g., JDBC sink to PostgreSQL, S3 sink to Data Lake)

Connect workers are scalable, fault-tolerant, and manage offset tracking automatically.

---

## 6. Change Data Capture (CDC) with Debezium

### 6.1 The Problem with Polling

The naive approach to keeping a downstream system (ODS, Data Lake, DWH) in sync with an operational database is polling: run a query every N minutes and fetch rows where `updated_at > last_poll_time`.

This fails in practice because:
- **Deletes are invisible** — a deleted row leaves no trace for a polling query to find.
- **`updated_at` is unreliable** — not all tables have it; some updates bypass ORM hooks that would set it.
- **You are scanning the source database** — every poll is a read load on your production CBS.
- **Latency is bounded by poll interval** — you cannot achieve sub-second propagation.

CDC reads the database's **transaction log** (the WAL in PostgreSQL, binlog in MySQL) instead of querying the tables. Every committed INSERT, UPDATE, and DELETE is already recorded there — for the database's own crash recovery. CDC captures those entries and publishes them as events.

### 6.2 How PostgreSQL WAL-Based CDC Works

PostgreSQL writes every committed transaction to the **Write-Ahead Log (WAL)** before returning success to the client. This is the basis of PostgreSQL's own durability guarantee.

CDC uses **logical replication**, a PostgreSQL feature that decodes the WAL from its binary format into a stream of logical change events (row-level INSERT/UPDATE/DELETE with before and after images).

```
PostgreSQL CBS
├── tables: transactions, accounts, customers
└── WAL (Write-Ahead Log)
    ├── LSN 0/1A2B3C: BEGIN txn_id=9001
    ├── LSN 0/1A2B4D: INSERT INTO transactions VALUES (...)
    ├── LSN 0/1A2B5E: UPDATE accounts SET balance = 84000 WHERE id = ACC-123
    └── LSN 0/1A2B6F: COMMIT txn_id=9001
                │
                ▼ logical replication slot
         ┌──────────────┐
         │   Debezium   │  ← reads WAL via replication slot, decodes to JSON
         │  CDC Engine  │
         └──────┬───────┘
                │ publishes one Kafka event per change
                ▼
         Kafka Topic: cbs.public.transactions
```

**Replication Slot** — a PostgreSQL object that tells the WAL "do not discard these entries until this slot has consumed them." This prevents Debezium from missing changes if it restarts, at the cost of WAL growth if the slot falls behind.

**LSN (Log Sequence Number)** — a monotonically increasing identifier for each WAL position. Debezium tracks the last-processed LSN, enabling exactly-once delivery on reconnect.

### 6.3 The Debezium Event Structure

Every Debezium event carries a `before` and `after` image of the row, plus metadata:

```json
{
  "before": null,
  "after": {
    "txn_id": "TXN-2024-001",
    "account_id": "ACC-00123456",
    "amount": 15000.00,
    "txn_type": "MURABAHA_PAYMENT",
    "status": "POSTED",
    "txn_date": "2024-01-15"
  },
  "op": "c",
  "ts_ms": 1705329120000,
  "source": {
    "db": "al_noor_cbs",
    "table": "transactions",
    "lsn": 178392,
    "txId": 9001
  }
}
```

`op` values: `c` = create (INSERT), `u` = update, `d` = delete, `r` = read (snapshot).

For an UPDATE, `before` contains the row state before the change, `after` contains the new state. A downstream SCD Type 2 handler uses `before` to close the existing row and `after` to open the new one.

### 6.4 Debezium Connector Configuration — Al-Noor CBS

```json
{
  "name": "al-noor-cbs-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "al-noor-cbs-primary.internal",
    "database.port": "5432",
    "database.user": "debezium_reader",
    "database.password": "${file:/opt/secrets/dbz.properties:password}",
    "database.dbname": "al_noor_cbs",
    "plugin.name": "pgoutput",
    "slot.name": "debezium_al_noor_slot",
    "table.include.list": "public.transactions,public.accounts,public.customers",
    "topic.prefix": "cbs",
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.add.fields": "op,table,lsn,source.ts_ms",
    "heartbeat.interval.ms": "10000",
    "publication.name": "debezium_publication"
  }
}
```

The `ExtractNewRecordState` transform flattens the envelope to just the `after` image plus metadata fields — simpler for downstream consumers that do not need the full before/after structure.

### 6.5 CDC vs. Batch Extract — Decision Framework

| Criterion | Batch Extract | CDC |
|---|---|---|
| Deletes captured | No | Yes |
| Source DB load | High (periodic scan) | Low (WAL read only) |
| Latency | Bounded by batch interval | Near-real-time (seconds) |
| Operational complexity | Low | Higher (replication slot management) |
| Exactly-once guarantee | Depends on `updated_at` reliability | Yes (LSN tracking) |
| SAMA auditability | Partial | Complete — every state transition captured |

For the Al-Noor CBS: CDC is the correct choice. The CBS processes 500,000 transactions per day and supports AML alerts that must fire within 30 seconds. A 5-minute batch extract cannot meet that SLA. Batch extract is retained only for legacy source systems that do not expose a WAL.

---

## 7. Apache Airflow

### 7.1 The Problem Airflow Solves

A data pipeline is rarely a single step. The Al-Noor nightly DWH load, for example, involves:

1. Waiting for the CBS extract to land in S3
2. Running data quality checks on the extract
3. Loading the extract into the ODS
4. Running the Spark ELT job to build `FACT_TRANSACTION`
5. Running dbt models for the dimension tables
6. Validating row counts against expected thresholds
7. Triggering SAMA report generation
8. Sending a completion notification

Each step depends on the previous one completing successfully. If step 4 fails, steps 5–8 must not run. If step 4 fails at 2 AM, someone needs to know immediately. If the same pipeline runs every night, it needs to be scheduled reliably.

Cron handles scheduling. Shell scripts handle sequencing. But neither handles **dependency tracking**, **retries with backoff**, **failure alerting**, **backfilling missed runs**, or **visibility into what ran and what failed**. Airflow handles all of these.

### 7.2 Core Concepts

**DAG (Directed Acyclic Graph)** — the pipeline definition. A DAG is a Python file that defines tasks and the dependencies between them. "Acyclic" means there are no loops — execution moves forward only.

**Task** — a single unit of work within a DAG. Tasks are implemented using **Operators**.

**Operator** — a template for a task type:
- `PythonOperator` — runs a Python function
- `BashOperator` — runs a shell command
- `PostgresOperator` — executes SQL against a PostgreSQL connection
- `SparkSubmitOperator` — submits a Spark job to a cluster
- `S3KeySensor` — waits until a specific file appears in S3
- `HttpSensor` — polls an HTTP endpoint until it returns a success status

**DAG Run** — one execution of the DAG. Every scheduled run, plus any manually triggered runs, produce a separate DAG Run with its own state.

**Task Instance** — one execution of one Task within one DAG Run. Each Task Instance has a state: `queued`, `running`, `success`, `failed`, `up_for_retry`, `skipped`.

### 7.3 The Airflow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AIRFLOW CLUSTER                         │
│                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │Webserver │    │  Scheduler   │    │    Metadata DB   │  │
│  │(UI + API)│    │(DAG parsing +│◄──►│  (PostgreSQL)    │  │
│  └──────────┘    │ task trigger)│    │  DAG runs,       │  │
│                  └──────┬───────┘    │  task states,    │  │
│                         │ task queue │  connections,    │  │
│                         ▼           │  variables       │  │
│                  ┌──────────────┐   └──────────────────┘  │
│                  │ Message Queue│                           │
│                  │(Redis/RabbitMQ                          │
│                  └──────┬───────┘                          │
│                         │                                  │
│              ┌──────────┼──────────┐                       │
│              ▼          ▼          ▼                       │
│         ┌────────┐ ┌────────┐ ┌────────┐                  │
│         │Worker 1│ │Worker 2│ │Worker 3│                  │
│         └────────┘ └────────┘ └────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

**Webserver** — serves the Airflow UI and REST API. Does not execute any tasks.

**Scheduler** — parses DAG files, determines which tasks are due to run, checks dependencies, and places ready tasks onto the work queue. The scheduler runs continuously, typically at a 5–30 second loop interval.

**Workers** — pull tasks from the queue and execute them. Workers are stateless — they execute one task, report the result to the metadata DB, and pick up the next task. Workers can be scaled horizontally.

**Metadata Database** — PostgreSQL (production standard) storing all state: DAG definitions, DAG runs, task instances, connections, variables, XCom values. The metadata DB is the single source of truth for the Airflow cluster.

**Message Queue** — Redis or RabbitMQ, used by the CeleryExecutor to distribute tasks to workers. Not required if using the LocalExecutor (single-machine) or KubernetesExecutor.

### 7.4 Executors

The **Executor** determines how tasks are run:

| Executor | Where tasks run | Use case |
|---|---|---|
| `SequentialExecutor` | In the scheduler process, one at a time | Development only |
| `LocalExecutor` | Subprocesses on the scheduler machine | Small team, single host |
| `CeleryExecutor` | Distributed workers via message queue | Production, horizontal scale |
| `KubernetesExecutor` | Each task as a Kubernetes Pod | Cloud-native, isolation per task |

Al-Noor's production deployment uses `CeleryExecutor` with Redis as the broker, running workers on 4 dedicated nodes, each with 8 CPU cores and 32 GB RAM.

### 7.5 Writing a DAG — Al-Noor Nightly DWH Load

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.sensors.s3_key_sensor import S3KeySensor
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-engineering',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': True,
    'email': ['de-alerts@al-noor.sa'],
    'sla': timedelta(hours=3),        # alert if DAG takes > 3 hours
}

with DAG(
    dag_id='al_noor_nightly_dwh_load',
    default_args=default_args,
    schedule_interval='0 1 * * *',   # 01:00 AST every night
    start_date=datetime(2024, 1, 1),
    catchup=False,                    # do not backfill missed runs on deployment
    tags=['dwh', 'critical', 'sama'],
) as dag:

    # Wait for CBS extract to appear in S3
    wait_for_extract = S3KeySensor(
        task_id='wait_for_cbs_extract',
        bucket_name='al-noor-datalake',
        bucket_key='raw/cbs/transactions/{{ ds }}/extract.parquet',
        timeout=3600,
        poke_interval=60,
    )

    # Validate row counts on raw extract
    validate_extract = PythonOperator(
        task_id='validate_extract',
        python_callable=validate_cbs_extract,
        op_kwargs={'date': '{{ ds }}'},
    )

    # Load ODS
    load_ods = PostgresOperator(
        task_id='load_ods_transactions',
        postgres_conn_id='al_noor_ods',
        sql='sql/load_ods_transactions.sql',
        parameters={'load_date': '{{ ds }}'},
    )

    # Spark ELT: ODS → FACT_TRANSACTION in Delta Lake
    spark_etl = SparkSubmitOperator(
        task_id='spark_fact_transaction_etl',
        application='s3://al-noor-code/spark/etl_fact_transaction.py',
        conn_id='spark_al_noor',
        application_args=['--date', '{{ ds }}'],
        conf={
            'spark.executor.memory': '8g',
            'spark.executor.cores': '4',
            'spark.sql.shuffle.partitions': '200',
        },
    )

    # Validate output row counts
    validate_output = PythonOperator(
        task_id='validate_fact_output',
        python_callable=validate_fact_row_count,
        op_kwargs={'date': '{{ ds }}', 'threshold': 0.95},
    )

    # Trigger SAMA report generation
    trigger_sama_report = PythonOperator(
        task_id='trigger_sama_daily_report',
        python_callable=trigger_sama_pipeline,
    )

    # Define dependencies
    wait_for_extract >> validate_extract >> load_ods >> spark_etl >> validate_output >> trigger_sama_report
```

### 7.6 Scheduling, Catchup, and Backfill

**`schedule_interval`** uses cron expressions or Airflow presets (`@daily`, `@hourly`). Internally, Airflow uses the `data_interval_start` and `data_interval_end` of each DAG Run to parameterise tasks — `{{ ds }}` renders to `data_interval_start` in YYYY-MM-DD format.

**Catchup** — if a DAG is paused for 10 days and then re-enabled with `catchup=True`, Airflow will create 10 DAG Runs to cover the missed intervals. For the DWH load pipeline, catchup is disabled (`catchup=False`) to prevent an accidental 10-day backfill from overloading the CBS database.

**Backfill** — deliberate reprocessing of historical intervals via CLI:
```bash
airflow dags backfill \
  --start-date 2024-01-01 \
  --end-date 2024-01-15 \
  al_noor_nightly_dwh_load
```

This is used when a bug is fixed in the ETL logic and historical fact data needs to be recomputed.

### 7.7 SLAs and Alerting

An SLA in Airflow is a maximum time a task or DAG run is expected to take. If exceeded, Airflow calls the `sla_miss_callback` and logs the miss. This is not a hard stop — the task continues running.

```python
def sla_miss_alert(dag, task_list, blocking_task_list, slas, blocking_tis):
    send_alert(
        channel='#data-engineering-alerts',
        message=f"SLA MISS: {dag.dag_id} tasks {task_list} exceeded SLA"
    )
```

For the Al-Noor nightly load with a 7 AM SAMA report deadline, the DAG SLA is set to 3 hours (the job starts at 1 AM). If any task has not completed by 4 AM, the on-call engineer is paged.

---

## 8. How the Components Connect — The Al-Noor Ingestion Pipeline End to End

```
CBS (PostgreSQL)
      │
      │ WAL (logical replication)
      ▼
  Debezium CDC Connector
      │
      │ JSON events per row change
      ▼
  Kafka Topic: cbs.public.transactions
      │
      ├─────────────────────────────────────┐
      │                                     │
      ▼                                     ▼
  Consumer Group: aml-engine          Consumer Group: dwh-etl
  (AML alert within 30s)              (batch ELT via Airflow)
                                            │
                                            │ Airflow DAG (01:00 AST)
                                            ▼
                                      Spark ELT Job
                                      (ODS → Delta Lake FACT_TRANSACTION)
                                            │
                                            ▼
                                      Snowflake (EDW)
                                            │
                                            ▼
                                      SAMA Report (07:00 AST)
```

The CDC path and the batch path are independent. The AML engine consumes from Kafka directly for near-real-time alerting. The DWH ELT batch job, orchestrated by Airflow, reads from the ODS (which is itself kept current by a separate Kafka consumer) and produces the daily FACT_TRANSACTION load that feeds the SAMA 7 AM report.

---

## 9. Key Design Decisions — Summary

| Decision | Rationale |
|---|---|
| Kafka over a message queue (RabbitMQ, SQS) | Kafka retains events; consumers can replay. A message queue deletes on consumption. |
| CDC over batch polling | Captures deletes; no source DB scan; sub-minute latency; SAMA-complete audit trail. |
| Kappa over Lambda | Single processing layer. Kafka offset replay replaces a separate batch layer. Simpler operationally. |
| Spark over MapReduce | In-memory intermediate data; DataFrame API; Catalyst optimiser; Delta Lake integration. |
| Airflow over cron | Dependency tracking, retries, SLA enforcement, backfill, UI visibility. Cron does none of these. |
| Partition by account_id in Kafka | Preserves event ordering per account. Required for correct SCD Type 2 processing. |

---

*This document covers the architecture covered in Day 7 of the Data Engineering Intermediate Programme. The Snowflake section — EDW design, RBAC, Time Travel, and the Al-Noor DWH construction — is covered in a separate reference document.*
