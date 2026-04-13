# Understanding MongoDB

## From Zero to Hero — A Complete Practical Guide

### ShopSmart E-Commerce Edition

-----

# CHAPTER 1 — What is MongoDB and Why Does It Exist?

-----

## The Problem With Tables

Relational databases like PostgreSQL store data in tables — rows and
columns. This works beautifully for structured, predictable data.

But imagine you are storing product information for ShopSmart.

Some products have one image. Some have twenty.
Some products have a colour attribute. Some have a size. Some have both.
Some have neither — they have a warranty period instead.
Electronics have voltage specs. Clothing has fabric composition.

In a relational table, you have two bad options:

**Option A — Add a column for every possible attribute:**

```
┌────────────┬────────┬───────┬─────────┬─────────┬───────────┬─────────┐
│ product_id │  name  │ colour│  size   │ voltage │  warranty │ fabric  │
├────────────┼────────┼───────┼─────────┼─────────┼───────────┼─────────┤
│ P001       │ T-Shirt│  Red  │    M    │  NULL   │   NULL    │ Cotton  │
│ P002       │ Laptop │  NULL │  NULL   │  240V   │  2 years  │  NULL   │
│ P003       │ Shoes  │ Black │   42    │  NULL   │   NULL    │  NULL   │
└────────────┴────────┴───────┴─────────┴─────────┴───────────┴─────────┘

Result: 80% of every row is NULL. Wasteful and inflexible.
```

**Option B — A separate attributes table:**

```
┌────────────┬───────────────┬────────────┐
│ product_id │ attribute_name│    value   │
├────────────┼───────────────┼────────────┤
│ P001       │ colour        │ Red        │
│ P001       │ size          │ M          │
│ P001       │ fabric        │ Cotton     │
│ P002       │ voltage       │ 240V       │
│ P002       │ warranty      │ 2 years    │
└────────────┴───────────────┴────────────┘

Result: Every query needs a JOIN. Querying "all red products"
        requires filtering a generic value column. Slow and messy.
```

MongoDB solves this differently. Instead of forcing every product
into the same rigid row structure, each product gets its own
**document** — a flexible container that holds exactly the fields
that product needs and nothing more.

-----

## What MongoDB Is

MongoDB is a **document database**. Instead of tables and rows,
it stores data as **documents** inside **collections**.

A document looks like this:

```json
{
  "_id": "P001",
  "name": "Classic Cotton T-Shirt",
  "category": "Clothing",
  "price": 49.99,
  "attributes": {
    "colour": "Red",
    "size": "M",
    "fabric": "100% Cotton"
  },
  "images": [
    "https://shopsmart.com/images/tshirt-red-front.jpg",
    "https://shopsmart.com/images/tshirt-red-back.jpg"
  ],
  "in_stock": true,
  "stock_count": 142
}
```

And another product document in the same collection looks like this:

```json
{
  "_id": "P002",
  "name": "ProBook Laptop 15",
  "category": "Electronics",
  "price": 3499.99,
  "attributes": {
    "voltage": "240V",
    "warranty": "2 years",
    "processor": "Intel i7",
    "ram_gb": 16,
    "storage_gb": 512
  },
  "images": [
    "https://shopsmart.com/images/laptop-front.jpg"
  ],
  "in_stock": true,
  "stock_count": 23
}
```

Different fields. Different structures. Same collection.
MongoDB handles this naturally — no NULL columns, no awkward JOINs.

-----

## Key Terms — PostgreSQL vs MongoDB

|PostgreSQL Term|MongoDB Term              |Plain English                        |
|---------------|--------------------------|-------------------------------------|
|Database       |Database                  |The top-level container              |
|Table          |Collection                |A group of related records           |
|Row            |Document                  |One individual record                |
|Column         |Field                     |One piece of data within a record    |
|Primary Key    |_id                       |The unique identifier for each record|
|JOIN           |$lookup / embedding       |Combining data from two sources      |
|INDEX          |Index                     |A structure to speed up searches     |
|SELECT         |find()                    |Retrieving documents                 |
|INSERT         |insertOne() / insertMany()|Adding documents                     |
|UPDATE         |updateOne() / updateMany()|Modifying documents                  |
|DELETE         |deleteOne() / deleteMany()|Removing documents                   |

-----

## JSON and BSON

MongoDB documents are written in **JSON** format (JavaScript Object
Notation). JSON is the format you read and write when working with
MongoDB.

Internally, MongoDB stores data as **BSON** — Binary JSON. BSON
supports additional data types that JSON does not, like Date objects
and binary data. You do not need to think about BSON — MongoDB
handles the conversion automatically.

**JSON format basics:**

```json
{
  "text_field": "Hello",
  "number_field": 42,
  "decimal_field": 3.14,
  "boolean_field": true,
  "null_field": null,
  "array_field": [1, 2, 3],
  "nested_object": {
    "inner_field": "value"
  }
}
```

-----

## When to Use MongoDB vs PostgreSQL

**Use MongoDB when:**

- Your data structure varies between records (product catalogues,
  user profiles, content management)
- You need to store arrays or nested objects naturally
- Your schema changes frequently as the product evolves
- You are building a content catalogue, event log, or real-time feed

**Use PostgreSQL when:**

- Your data is highly structured and consistent (transactions,
  accounts, financial records)
- You need strict referential integrity between tables
- You need complex multi-table JOINs
- You are storing monetary values and need exact decimal arithmetic

**ShopSmart uses both:**

- MongoDB stores the product catalogue and customer reviews
  (flexible, varied structure)
- PostgreSQL stores orders and payments
  (structured, financial, needs ACID guarantees)

-----

# CHAPTER 2 — Documents and Collections

-----

## The Anatomy of a Document

A MongoDB document is a set of **field-value pairs** enclosed in
curly braces.

```
{
  "field_name": value,
  "another_field": another_value
}
```

Every document must have an **_id** field — the unique identifier.
If you do not provide one, MongoDB generates one automatically.

```json
{
  "_id": "CUST-00001",
  "full_name": "Ahmed Al-Omari",
  "email": "ahmed@example.com",
  "joined_date": "2024-01-15",
  "is_active": true
}
```

-----

## Nested Documents (Embedded Objects)

A field’s value can itself be a document. This is called an
**embedded document** or **nested document**.

```json
{
  "_id": "CUST-00001",
  "full_name": "Ahmed Al-Omari",
  "address": {
    "street": "123 King Fahd Road",
    "city": "Riyadh",
    "country": "Saudi Arabia",
    "postcode": "12345"
  },
  "preferences": {
    "newsletter": true,
    "sms_alerts": false,
    "language": "ar"
  }
}
```

The address is a complete object nested inside the customer document.
You can query on nested fields using **dot notation**:

```javascript
// Find all customers in Riyadh
db.customers.find({ "address.city": "Riyadh" })
```

-----

## Arrays

A field’s value can be an array — a list of values.
The values in an array can be strings, numbers, objects, or even
other arrays.

```json
{
  "_id": "P001",
  "name": "Classic Cotton T-Shirt",
  "tags": ["clothing", "casual", "summer", "cotton"],
  "available_sizes": ["XS", "S", "M", "L", "XL"],
  "images": [
    {
      "url": "https://shopsmart.com/img/tshirt-front.jpg",
      "alt": "Front view",
      "is_primary": true
    },
    {
      "url": "https://shopsmart.com/img/tshirt-back.jpg",
      "alt": "Back view",
      "is_primary": false
    }
  ]
}
```

MongoDB can query inside arrays naturally:

```javascript
// Find all products tagged as "summer"
db.products.find({ "tags": "summer" })

// Find all products available in size XL
db.products.find({ "available_sizes": "XL" })
```

-----

## The _id Field

Every document has a unique _id. Three options:

**Option 1 — Let MongoDB generate it (ObjectId)**

```json
{ "_id": ObjectId("507f1f77bcf86cd799439011") }
```

ObjectId is a 12-byte value that encodes a timestamp, machine ID,
and sequence number. Always unique. Always generated automatically
if you do not provide _id.

**Option 2 — Provide your own string ID**

```json
{ "_id": "CUST-00001" }
```

Good when you have a meaningful business identifier.

**Option 3 — Provide your own number**

```json
{ "_id": 12345 }
```

Good for simple sequential IDs.

-----

## Collections

A collection is a group of documents — like a table in SQL.
Documents in a collection do not need to have the same fields.

**ShopSmart collections:**

```
snb_practice database
├── customers        ← customer profiles
├── products         ← product catalogue
├── orders           ← order records
├── reviews          ← product reviews
└── categories       ← product categories
```

Creating a collection is implicit — MongoDB creates it automatically
the first time you insert a document into it.

```javascript
// This creates the customers collection if it does not exist
db.customers.insertOne({ "full_name": "Ahmed Al-Omari" })
```

-----

## Embedding vs Referencing

This is the most important design decision in MongoDB.

**Embedding** — store related data inside the same document.
**Referencing** — store a reference (like a foreign key) to a
document in another collection.

### Embedding Example

```json
{
  "_id": "ORD-00001",
  "customer_id": "CUST-00001",
  "order_date": "2025-03-01",
  "items": [
    {
      "product_id": "P001",
      "product_name": "Classic Cotton T-Shirt",
      "quantity": 2,
      "unit_price": 49.99,
      "subtotal": 99.98
    },
    {
      "product_id": "P047",
      "product_name": "Canvas Tote Bag",
      "quantity": 1,
      "unit_price": 29.99,
      "subtotal": 29.99
    }
  ],
  "total_amount": 129.97,
  "status": "DELIVERED"
}
```

The order items are embedded directly inside the order document.
To read an order with all its items: one query, one document.
No JOIN needed.

### Referencing Example

```json
{
  "_id": "ORD-00001",
  "customer_id": "CUST-00001",
  "item_ids": ["ITEM-001", "ITEM-002"],
  "total_amount": 129.97,
  "status": "DELIVERED"
}
```

The items live in a separate collection and are referenced by ID.
To read an order with all its items: two queries or a $lookup.

### When to Embed vs Reference

|Situation                              |Use      |
|---------------------------------------|---------|
|Data is always read together           |Embed    |
|Data is small and bounded (order items)|Embed    |
|Data rarely changes after creation     |Embed    |
|Data is large and grows unboundedly    |Reference|
|Data is shared across many documents   |Reference|
|Data needs to be queried independently |Reference|

**ShopSmart rule of thumb:**

- Order items → embed inside the order (always read together)
- Customer address → embed inside the customer (belongs to one customer)
- Product details → reference from orders (product exists independently,
  can change, is shared across thousands of orders)

-----

# CHAPTER 3 — CRUD Operations

-----

## Connecting and Selecting a Database

```javascript
// In MongoDB shell or mongosh
use snb_practice
// MongoDB creates the database when you first insert data
```

-----

## INSERT — Adding Documents

### insertOne() — Add a Single Document

```javascript
db.customers.insertOne({
  "_id": "CUST-00001",
  "full_name": "Ahmed Al-Omari",
  "email": "ahmed.alomari@example.com",
  "phone": "+966501234567",
  "address": {
    "street": "123 King Fahd Road",
    "city": "Riyadh",
    "country": "Saudi Arabia"
  },
  "joined_date": new Date("2024-01-15"),
  "total_orders": 0,
  "is_active": true,
  "tags": ["premium", "early_adopter"]
})
```

**What MongoDB returns:**

```json
{
  "acknowledged": true,
  "insertedId": "CUST-00001"
}
```

-----

### insertMany() — Add Multiple Documents at Once

```javascript
db.products.insertMany([
  {
    "_id": "P001",
    "name": "Classic Cotton T-Shirt",
    "category": "Clothing",
    "price": 49.99,
    "stock": 142,
    "tags": ["clothing", "casual", "cotton"],
    "rating": 4.3,
    "is_active": true
  },
  {
    "_id": "P002",
    "name": "ProBook Laptop 15",
    "category": "Electronics",
    "price": 3499.99,
    "stock": 23,
    "tags": ["electronics", "laptop", "work"],
    "rating": 4.7,
    "is_active": true
  },
  {
    "_id": "P003",
    "name": "Running Shoes",
    "category": "Footwear",
    "price": 189.99,
    "stock": 0,
    "tags": ["footwear", "sport", "running"],
    "rating": 4.1,
    "is_active": false
  }
])
```

**What MongoDB returns:**

```json
{
  "acknowledged": true,
  "insertedCount": 3,
  "insertedIds": {
    "0": "P001",
    "1": "P002",
    "2": "P003"
  }
}
```

-----

## FIND — Retrieving Documents

### find() — Get All Documents

```javascript
// Get every document in the collection
db.customers.find()

// Get every document, displayed neatly
db.customers.find().pretty()
```

### findOne() — Get the First Matching Document

```javascript
// Get one customer by ID
db.customers.findOne({ "_id": "CUST-00001" })
```

-----

### Filtering with find()

The first argument to find() is the **filter** — a document
describing what you are looking for.

```javascript
// Exact match
db.products.find({ "category": "Electronics" })

// Multiple conditions (AND — both must be true)
db.products.find({
  "category": "Electronics",
  "is_active": true
})

// Nested field using dot notation
db.customers.find({ "address.city": "Riyadh" })

// Field exists
db.products.find({ "discount_price": { $exists: true } })

// Field does not exist
db.products.find({ "discount_price": { $exists: false } })
```

-----

### Comparison Operators

```javascript
// Greater than
db.products.find({ "price": { $gt: 100 } })

// Greater than or equal
db.products.find({ "price": { $gte: 49.99 } })

// Less than
db.products.find({ "price": { $lt: 500 } })

// Less than or equal
db.products.find({ "price": { $lte: 189.99 } })

// Not equal
db.products.find({ "category": { $ne: "Electronics" } })

// In a list of values
db.products.find({ "category": { $in: ["Clothing", "Footwear"] } })

// Not in a list
db.products.find({ "category": { $nin: ["Electronics"] } })

// Between two values (price between 50 and 200)
db.products.find({
  "price": { $gte: 50, $lte: 200 }
})
```

-----

### Logical Operators

```javascript
// AND — explicit (useful when filtering same field twice)
db.products.find({
  $and: [
    { "price": { $gte: 50 } },
    { "price": { $lte: 200 } }
  ]
})

// OR — either condition can be true
db.products.find({
  $or: [
    { "category": "Electronics" },
    { "price": { $gt: 1000 } }
  ]
})

// NOT
db.products.find({
  "category": { $not: { $eq: "Electronics" } }
})

// NOR — neither condition is true
db.products.find({
  $nor: [
    { "category": "Electronics" },
    { "is_active": false }
  ]
})
```

-----

### Array Queries

```javascript
// Find documents where tags array contains "summer"
db.products.find({ "tags": "summer" })

// Find documents where tags contains ALL of these values
db.products.find({
  "tags": { $all: ["casual", "cotton"] }
})

// Find documents where tags array has exactly 3 elements
db.products.find({
  "tags": { $size: 3 }
})

// Find documents where at least one item in an array
// matches a condition
db.orders.find({
  "items": {
    $elemMatch: {
      "unit_price": { $gt: 100 },
      "quantity": { $gte: 2 }
    }
  }
})
```

-----

### Projection — Choosing Which Fields to Return

The second argument to find() is the **projection** — which fields
to include or exclude.

```javascript
// Include only specific fields (1 = include)
db.customers.find(
  { "address.city": "Riyadh" },
  { "full_name": 1, "email": 1, "address.city": 1 }
)
// Returns: _id (always included), full_name, email, address.city

// Exclude specific fields (0 = exclude)
db.customers.find(
  {},
  { "phone": 0, "address": 0 }
)
// Returns everything except phone and address

// Exclude _id
db.customers.find(
  { "is_active": true },
  { "full_name": 1, "email": 1, "_id": 0 }
)
// Returns: full_name and email only — no _id
```

**Why projection matters:**
Fetching only the fields you need reduces the amount of data
transferred over the network. On a collection with millions of
documents and large embedded objects, this is a significant
performance difference.

-----

### Sorting, Limiting, and Skipping

```javascript
// Sort by price ascending (1 = ascending)
db.products.find().sort({ "price": 1 })

// Sort by price descending (-1 = descending)
db.products.find().sort({ "price": -1 })

// Sort by category ascending, then price descending
db.products.find().sort({ "category": 1, "price": -1 })

// Limit results to 10 documents
db.products.find().limit(10)

// Skip the first 20 documents (for pagination)
db.products.find().skip(20).limit(10)

// All together — page 3 of results, 10 per page, sorted by price
db.products.find(
  { "is_active": true },
  { "name": 1, "price": 1 }
)
.sort({ "price": 1 })
.skip(20)
.limit(10)
```

-----

### Counting Documents

```javascript
// Count all documents in a collection
db.products.countDocuments()

// Count with a filter
db.products.countDocuments({ "category": "Electronics" })

// Count documents matching a complex filter
db.products.countDocuments({
  "is_active": true,
  "price": { $lt: 500 }
})
```

-----

## UPDATE — Modifying Documents

### updateOne() — Update the First Matching Document

```javascript
// Syntax
db.collection.updateOne(
  { filter },       // which document to update
  { update },       // what to change
  { options }       // optional settings
)

// Example: update one customer's email
db.customers.updateOne(
  { "_id": "CUST-00001" },
  { $set: { "email": "new.email@example.com" } }
)
```

### updateMany() — Update All Matching Documents

```javascript
// Mark all Electronics products as featured
db.products.updateMany(
  { "category": "Electronics" },
  { $set: { "is_featured": true } }
)

// Deactivate all out-of-stock products
db.products.updateMany(
  { "stock": 0 },
  { $set: { "is_active": false } }
)
```

-----

## Update Operators — The Full Set

### $set — Set a Field Value

```javascript
// Add or update a field
db.products.updateOne(
  { "_id": "P001" },
  {
    $set: {
      "price": 44.99,
      "discount_price": 39.99,
      "on_sale": true
    }
  }
)
// If the field exists: updates it
// If the field does not exist: creates it
```

-----

### $unset — Remove a Field

```javascript
// Remove the discount fields when sale ends
db.products.updateOne(
  { "_id": "P001" },
  {
    $unset: {
      "discount_price": "",
      "on_sale": ""
    }
  }
)
// The value in $unset does not matter — "" is conventional
```

-----

### $inc — Increment a Number

```javascript
// Increase stock count by 50
db.products.updateOne(
  { "_id": "P001" },
  { $inc: { "stock": 50 } }
)

// Decrease stock count by 1 (when an order is placed)
db.products.updateOne(
  { "_id": "P001" },
  { $inc: { "stock": -1 } }
)

// Increment total_orders for a customer
db.customers.updateOne(
  { "_id": "CUST-00001" },
  { $inc: { "total_orders": 1 } }
)
```

-----

### $push — Add an Item to an Array

```javascript
// Add a new tag to a product
db.products.updateOne(
  { "_id": "P001" },
  { $push: { "tags": "bestseller" } }
)

// Add multiple items to an array at once
db.products.updateOne(
  { "_id": "P001" },
  { $push: { "tags": { $each: ["sale", "clearance"] } } }
)
```

-----

### $pull — Remove an Item from an Array

```javascript
// Remove a specific tag
db.products.updateOne(
  { "_id": "P001" },
  { $pull: { "tags": "clearance" } }
)

// Remove all tags that match a condition
db.products.updateOne(
  { "_id": "P001" },
  { $pull: { "tags": { $in: ["sale", "clearance"] } } }
)
```

-----

### $addToSet — Add to Array Only if Not Already Present

```javascript
// Add "summer" to tags — but only if it is not already there
db.products.updateOne(
  { "_id": "P001" },
  { $addToSet: { "tags": "summer" } }
)
// If "summer" already exists in tags: no change
// If "summer" does not exist: adds it
// Unlike $push which adds duplicates freely
```

-----

### The Critical Mistake — Overwriting vs Updating

```javascript
// WRONG — this replaces the ENTIRE document
// with just the price field
db.products.updateOne(
  { "_id": "P001" },
  { "price": 44.99 }
)
// Result: { "_id": "P001", "price": 44.99 }
// Everything else — name, category, stock — is GONE

// CORRECT — use $set to update only the price field
db.products.updateOne(
  { "_id": "P001" },
  { $set: { "price": 44.99 } }
)
// Result: all fields preserved, only price changed
```

This is the most common beginner mistake in MongoDB.
Always use an update operator like $set.
Never pass a plain document as the update argument.

-----

## DELETE — Removing Documents

### deleteOne() — Remove the First Matching Document

```javascript
// Remove a specific product
db.products.deleteOne({ "_id": "P003" })
```

### deleteMany() — Remove All Matching Documents

```javascript
// Remove all inactive products
db.products.deleteMany({ "is_active": false })

// Remove all products with zero stock
db.products.deleteMany({ "stock": 0 })

// Remove ALL documents (dangerous — use with care)
db.products.deleteMany({})
```

### upsert — Update if Exists, Insert if Not

```javascript
// Update the document if found, insert it if not found
db.products.updateOne(
  { "_id": "P099" },
  {
    $set: {
      "name": "New Product",
      "price": 99.99,
      "is_active": true
    }
  },
  { upsert: true }
)
// If P099 exists: updates it
// If P099 does not exist: creates a new document
```

-----

# CHAPTER 4 — The Aggregation Pipeline

-----

## What is a Pipeline?

A pipeline is a sequence of stages. Each stage takes the documents
from the previous stage, does something to them, and passes the
result to the next stage.

Think of it like an assembly line:

```
Documents enter → [Stage 1] → [Stage 2] → [Stage 3] → Result exits

Example:
All orders → Filter to 2025 orders → Group by customer → Sort by total → Top 10
```

The MongoDB aggregation pipeline is the tool for answering complex
business questions — “Who are our top 10 customers by spend this
year?” — that a simple find() cannot answer.

-----

## $match — Filter Documents (like WHERE in SQL)

```javascript
db.orders.aggregate([
  {
    $match: {
      "status": "DELIVERED",
      "order_date": { $gte: new Date("2025-01-01") }
    }
  }
])
```

**Rule:** Always put $match as early as possible in the pipeline.
It reduces the number of documents flowing into later stages —
making the entire pipeline faster.

-----

## $group — Group and Aggregate (like GROUP BY in SQL)

```javascript
// Total revenue per category
db.orders.aggregate([
  {
    $group: {
      "_id": "$category",          // group by this field
      "total_revenue": {
        $sum: "$total_amount"      // sum of total_amount per group
      },
      "order_count": {
        $sum: 1                    // count of documents per group
      },
      "avg_order_value": {
        $avg: "$total_amount"      // average per group
      }
    }
  }
])
```

**$group accumulators:**

|Accumulator|What it does                        |
|-----------|------------------------------------|
|$sum       |Adds up values                      |
|$avg       |Calculates the average              |
|$min       |Finds the minimum value             |
|$max       |Finds the maximum value             |
|$count     |Counts documents                    |
|$push      |Collects values into an array       |
|$addToSet  |Collects unique values into an array|
|$first     |Gets the first value in the group   |
|$last      |Gets the last value in the group    |

-----

## $sort — Sort Results (like ORDER BY in SQL)

```javascript
db.orders.aggregate([
  { $group: {
      "_id": "$customer_id",
      "total_spent": { $sum: "$total_amount" }
  }},
  { $sort: { "total_spent": -1 } }  // descending
])
```

-----

## $limit — Keep Only the First N Documents

```javascript
// Top 5 customers by spend
db.orders.aggregate([
  { $group: {
      "_id": "$customer_id",
      "total_spent": { $sum: "$total_amount" }
  }},
  { $sort: { "total_spent": -1 } },
  { $limit: 5 }
])
```

-----

## $project — Choose and Reshape Fields (like SELECT in SQL)

```javascript
// Show only name and price, add a discounted price field
db.products.aggregate([
  {
    $project: {
      "name": 1,
      "price": 1,
      "discounted_price": { $multiply: ["$price", 0.9] },
      "category": 1,
      "_id": 0
    }
  }
])
```

**$project computed fields:**

```javascript
db.orders.aggregate([
  {
    $project: {
      "order_id": "$_id",
      "customer_id": 1,
      "total_amount": 1,
      // Add a new field using arithmetic
      "vat_amount": { $multiply: ["$total_amount", 0.15] },
      // Concatenate strings
      "order_label": {
        $concat: ["Order-", "$_id"]
      },
      // Conditional field
      "is_large_order": {
        $cond: {
          if: { $gte: ["$total_amount", 500] },
          then: true,
          else: false
        }
      }
    }
  }
])
```

-----

## $lookup — Join Two Collections (like JOIN in SQL)

```javascript
// Get orders with full customer details
db.orders.aggregate([
  {
    $lookup: {
      from: "customers",          // the other collection
      localField: "customer_id",  // field in orders
      foreignField: "_id",        // field in customers
      as: "customer_details"      // name for the joined data
    }
  }
])

// Result: each order document gets a customer_details array
// containing the matching customer document
```

**Then flatten the result with $unwind:**

```javascript
db.orders.aggregate([
  {
    $lookup: {
      from: "customers",
      localField: "customer_id",
      foreignField: "_id",
      as: "customer"
    }
  },
  // $unwind turns the customer array into a single object
  { $unwind: "$customer" },
  {
    $project: {
      "order_date": 1,
      "total_amount": 1,
      "status": 1,
      "customer_name": "$customer.full_name",
      "customer_city": "$customer.address.city"
    }
  }
])
```

-----

## $unwind — Deconstruct an Array

```javascript
// An order document has an items array:
// { "_id": "ORD-001", "items": [ {...}, {...}, {...} ] }

// $unwind creates one document per array element:
db.orders.aggregate([
  { $unwind: "$items" }
])

// Result:
// { "_id": "ORD-001", "items": { first item } }
// { "_id": "ORD-001", "items": { second item } }
// { "_id": "ORD-001", "items": { third item } }
```

**Practical use — revenue per product:**

```javascript
db.orders.aggregate([
  // Only delivered orders
  { $match: { "status": "DELIVERED" } },
  // Break out each order item into its own document
  { $unwind: "$items" },
  // Group by product
  {
    $group: {
      "_id": "$items.product_id",
      "product_name": { $first: "$items.product_name" },
      "total_quantity_sold": { $sum: "$items.quantity" },
      "total_revenue": { $sum: "$items.subtotal" }
    }
  },
  // Sort by revenue descending
  { $sort: { "total_revenue": -1 } },
  // Top 10 products
  { $limit: 10 }
])
```

-----

## Building a Full Pipeline — Step by Step

**Business question:**
“What is the total spend and order count per city, for customers
who joined in 2024, for orders placed in 2025, sorted by total
spend descending?”

**Build it stage by stage:**

```javascript
db.orders.aggregate([

  // Stage 1: Only 2025 orders
  {
    $match: {
      "order_date": {
        $gte: new Date("2025-01-01"),
        $lt: new Date("2026-01-01")
      },
      "status": { $ne: "CANCELLED" }
    }
  },

  // Stage 2: Bring in customer details
  {
    $lookup: {
      from: "customers",
      localField: "customer_id",
      foreignField: "_id",
      as: "customer"
    }
  },

  // Stage 3: Flatten customer array
  { $unwind: "$customer" },

  // Stage 4: Filter to customers who joined in 2024
  {
    $match: {
      "customer.joined_date": {
        $gte: new Date("2024-01-01"),
        $lt: new Date("2025-01-01")
      }
    }
  },

  // Stage 5: Group by city
  {
    $group: {
      "_id": "$customer.address.city",
      "total_spend": { $sum: "$total_amount" },
      "order_count": { $sum: 1 },
      "avg_order_value": { $avg: "$total_amount" },
      "unique_customers": { $addToSet: "$customer_id" }
    }
  },

  // Stage 6: Add a unique customer count field
  {
    $project: {
      "city": "$_id",
      "total_spend": 1,
      "order_count": 1,
      "avg_order_value": { $round: ["$avg_order_value", 2] },
      "unique_customer_count": { $size: "$unique_customers" },
      "_id": 0
    }
  },

  // Stage 7: Sort by total spend
  { $sort: { "total_spend": -1 } }

])
```

-----

# CHAPTER 5 — Indexes in MongoDB

-----

## Why Indexes Matter

Without an index, every find() or aggregation $match scans every
document in the collection. This is called a **Collection Scan**.

With an index, MongoDB jumps directly to the matching documents.
This is called an **Index Scan**.

The difference in a collection with 1 million documents:

```
Collection Scan: reads 1,000,000 documents → result
Index Scan:      reads ~10 documents → result
```

-----

## explain() — See What MongoDB Is Doing

Before creating indexes, use explain() to see the current query plan.

```javascript
// See the execution plan for a query
db.products.find({ "category": "Electronics" }).explain("executionStats")
```

**Key fields to look at in the output:**

```
executionStats.executionTimeMillis    ← how long the query took
executionStats.totalDocsExamined      ← how many documents were scanned
executionStats.nReturned              ← how many documents were returned
queryPlanner.winningPlan.stage        ← COLLSCAN (bad) or IXSCAN (good)
```

**Bad output (no index):**

```json
{
  "executionStats": {
    "executionTimeMillis": 847,
    "totalDocsExamined": 1000000,
    "nReturned": 234
  },
  "queryPlanner": {
    "winningPlan": {
      "stage": "COLLSCAN"
    }
  }
}
```

Scanned 1,000,000 documents to return 234. Extremely inefficient.

**Good output (with index):**

```json
{
  "executionStats": {
    "executionTimeMillis": 2,
    "totalDocsExamined": 234,
    "nReturned": 234
  },
  "queryPlanner": {
    "winningPlan": {
      "stage": "IXSCAN",
      "indexName": "category_1"
    }
  }
}
```

Scanned exactly 234 documents and returned 234. Perfect.

-----

## Single Field Index

```javascript
// Create an index on the category field
db.products.createIndex({ "category": 1 })
// 1 = ascending, -1 = descending

// Name your index explicitly (recommended)
db.products.createIndex(
  { "category": 1 },
  { name: "idx_category" }
)

// Verify the index was created
db.products.getIndexes()
```

**Serves these queries:**

```javascript
db.products.find({ "category": "Electronics" })
db.products.find({ "category": { $in: ["Electronics", "Clothing"] } })
```

-----

## Compound Index

An index on multiple fields — serves queries that filter on
multiple fields together.

```javascript
// Index on category + price
db.products.createIndex(
  { "category": 1, "price": 1 },
  { name: "idx_category_price" }
)
```

**The ESR rule for compound index field order:**

1. **E**quality fields first (fields you filter with exact match)
1. **S**ort fields second (fields you sort on)
1. **R**ange fields last (fields you filter with $gt, $lt, etc.)

```javascript
// This query:
db.products.find({
  "category": "Electronics",        // Equality — put first
  "price": { $gte: 100, $lte: 500 } // Range — put last
}).sort({ "rating": -1 })           // Sort — put middle

// Best compound index for this query:
db.products.createIndex({
  "category": 1,   // Equality first
  "rating": -1,    // Sort second
  "price": 1       // Range last
})
```

**The prefix rule:**
A compound index on (A, B, C) also works for queries on:

- A alone
- A + B
- A + B + C

But NOT for B alone or C alone.

```
Index: { "category": 1, "price": 1, "rating": -1 }

✅ Works for: category
✅ Works for: category + price
✅ Works for: category + price + rating
❌ Does NOT: price alone
❌ Does NOT: rating alone
❌ Does NOT: price + rating
```

-----

## Multikey Index — Indexing Arrays

When you create an index on a field that contains an array,
MongoDB automatically creates a **multikey index** — it creates
an index entry for every element in the array.

```javascript
// Index on the tags array field
db.products.createIndex({ "tags": 1 })

// Now these queries use the index:
db.products.find({ "tags": "summer" })
db.products.find({ "tags": { $all: ["casual", "cotton"] } })
```

-----

## Text Index — Full Text Search

```javascript
// Create a text index on name and description
db.products.createIndex(
  { "name": "text", "description": "text" },
  { name: "idx_text_search" }
)

// Search for products matching "laptop wireless"
db.products.find(
  { $text: { $search: "laptop wireless" } }
)

// Search with relevance score
db.products.find(
  { $text: { $search: "laptop wireless" } },
  { "score": { $meta: "textScore" } }
).sort({ "score": { $meta: "textScore" } })
```

**Rules:**

- Only one text index per collection
- Text search is case-insensitive
- Words like “the”, “a”, “is” are ignored (stop words)

-----

## Partial Index — Index Only Some Documents

Like PostgreSQL, MongoDB can index only documents matching a
condition — creating a smaller, faster index.

```javascript
// Only index active products
db.products.createIndex(
  { "category": 1, "price": 1 },
  {
    partialFilterExpression: { "is_active": true },
    name: "idx_active_products"
  }
)

// This query uses the partial index (is_active: true is specified)
db.products.find({ "category": "Electronics", "is_active": true })

// This query does NOT use it (is_active filter not included)
db.products.find({ "category": "Electronics" })
```

-----

## Unique Index

```javascript
// Ensure no two customers have the same email
db.customers.createIndex(
  { "email": 1 },
  { unique: true, name: "idx_email_unique" }
)

// Attempting to insert a duplicate email now throws:
// E11000 duplicate key error collection: snb_practice.customers
// index: idx_email_unique dup key: { email: "ahmed@example.com" }
```

-----

## Managing Indexes

```javascript
// List all indexes on a collection
db.products.getIndexes()

// Drop a specific index by name
db.products.dropIndex("idx_category")

// Drop all indexes except _id
db.products.dropIndexes()

// Check index usage statistics
db.products.aggregate([{ $indexStats: {} }])
// Look at: accesses.ops — how many times each index was used
// An index with 0 accesses is a candidate for removal
```

-----

## The Write Trade-off (Same as PostgreSQL)

Every index speeds up reads but slows down writes.

```
Insert without indexes:   fast
Insert with 5 indexes:    MongoDB must update 5 index structures
                          per document inserted
```

**Rule:** Only create indexes that serve actual query patterns.
Profile your queries with explain() first. Index second.

-----

# CHAPTER 6 — Schema Design

-----

## The Core Question

Every schema design decision in MongoDB comes down to one question:

**“How will this data be queried?”**

The schema should match the access patterns of the application —
not the shape of the source data.

-----

## Pattern 1 — Embedding (One-to-Few)

Use when: one document contains a small, bounded number of
related items that are always read together.

```json
{
  "_id": "CUST-00001",
  "full_name": "Ahmed Al-Omari",
  "addresses": [
    {
      "type": "home",
      "street": "123 King Fahd Road",
      "city": "Riyadh",
      "is_default": true
    },
    {
      "type": "work",
      "street": "456 Olaya Street",
      "city": "Riyadh",
      "is_default": false
    }
  ]
}
```

A customer has a small, fixed number of addresses.
Addresses are always read with the customer. Embed them.

-----

## Pattern 2 — Referencing (One-to-Many)

Use when: one document relates to many other documents, or the
related documents are large, or they are queried independently.

```json
// Product document
{
  "_id": "P001",
  "name": "Classic Cotton T-Shirt",
  "category_id": "CAT-003"
}

// Category document (separate collection)
{
  "_id": "CAT-003",
  "name": "Clothing",
  "description": "All clothing items",
  "parent_category": "CAT-001"
}
```

Many products share one category. The category exists
independently. Reference it.

-----

## Pattern 3 — Hybrid (One-to-Many with Summary)

Use when: you frequently need summary data but occasionally
need full detail.

```json
// Order document — embeds item summary, references product
{
  "_id": "ORD-00001",
  "customer_id": "CUST-00001",
  "order_date": "2025-03-01",
  "total_amount": 129.97,
  "status": "DELIVERED",
  "items": [
    {
      "product_id": "P001",
      "product_name": "Classic Cotton T-Shirt",
      "quantity": 2,
      "unit_price": 49.99,
      "subtotal": 99.98
    }
  ]
}
```

Item details (name, price at time of order, quantity) are embedded
because they are always read with the order and they represent
the order at the time it was placed — even if the product price
changes later, the order history is preserved.

Product full details are referenced because the product exists
independently and the full product document is rarely needed
when reading order history.

-----

## The Unbounded Array Problem

**Never embed an array that can grow without limit.**

```json
// BAD — this product could have 100,000 reviews
{
  "_id": "P001",
  "name": "Classic Cotton T-Shirt",
  "reviews": [
    { "customer_id": "CUST-001", "rating": 5, "text": "..." },
    { "customer_id": "CUST-002", "rating": 4, "text": "..." },
    // ... potentially 100,000 more reviews
  ]
}
```

MongoDB documents have a 16MB size limit. An unbounded embedded
array will eventually hit this limit and break.

```json
// GOOD — reviews in a separate collection, referencing the product
{
  "_id": "REV-000001",
  "product_id": "P001",
  "customer_id": "CUST-00001",
  "rating": 5,
  "title": "Great quality",
  "body": "Very comfortable, true to size.",
  "date": "2025-03-15",
  "verified_purchase": true
}
```

-----

## Schema Design Checklist

Before finalising a schema, answer these questions:

```
1. What queries will the application run most often?
   → Design the schema to serve those queries efficiently

2. Will any arrays grow without bound?
   → If yes: use a separate collection with a reference

3. Is the related data always read together?
   → If yes: embed it
   → If no: reference it

4. Is the related data large (many fields, large text)?
   → If yes: reference it

5. Is the related data shared across many documents?
   → If yes: reference it (update once, reflected everywhere)
   → If no: embedding is fine
```

-----

# CHAPTER 7 — Common Mistakes

-----

### Mistake 1 — Using MongoDB Like a Relational Database

```javascript
// BAD — designing a normalised schema like PostgreSQL
// then doing $lookup for every query
db.orders.aggregate([
  { $lookup: { from: "customers", ... } },
  { $lookup: { from: "products", ... } },
  { $lookup: { from: "addresses", ... } },
  { $lookup: { from: "payments", ... } }
])

// This works but defeats the purpose of MongoDB.
// If you need this many JOINs for every query,
// consider whether PostgreSQL is the better tool.
```

-----

### Mistake 2 — Storing Money as Float

```javascript
// BAD
{ "price": 49.9900000000000002 }  // floating point error

// GOOD — use a string for display, store as NumberDecimal for calculation
{ "price": NumberDecimal("49.99") }

// Or store as integer cents
{ "price_cents": 4999 }
// Divide by 100 at the application layer for display
```

-----

### Mistake 3 — Not Using Projection

```javascript
// BAD — fetches entire documents including large arrays and text fields
db.products.find({ "category": "Electronics" })

// GOOD — fetch only what the query consumer needs
db.products.find(
  { "category": "Electronics" },
  { "name": 1, "price": 1, "stock": 1, "_id": 0 }
)
```

-----

### Mistake 4 — Missing Indexes on Query Fields

```javascript
// You run this query constantly
db.orders.find({ "customer_id": "CUST-00001", "status": "PENDING" })

// But there is no index on customer_id or status
// Every query scans the entire orders collection

// Fix:
db.orders.createIndex(
  { "customer_id": 1, "status": 1 },
  { name: "idx_orders_customer_status" }
)
```

-----

### Mistake 5 — Growing Arrays Without Limit

Already covered in Chapter 6. Never embed arrays that can grow
without bound. Use a separate collection with a reference instead.

-----

# CHAPTER 8 — Quick Reference Card

-----

## CRUD Operations

|Operation       |Command                                     |
|----------------|--------------------------------------------|
|Insert one      |db.col.insertOne({…})                       |
|Insert many     |db.col.insertMany([{…},{…}])                |
|Find all        |db.col.find()                               |
|Find with filter|db.col.find({ field: value })               |
|Find one        |db.col.findOne({ field: value })            |
|Update one      |db.col.updateOne({ filter }, { $set: {…} }) |
|Update many     |db.col.updateMany({ filter }, { $set: {…} })|
|Delete one      |db.col.deleteOne({ filter })                |
|Delete many     |db.col.deleteMany({ filter })               |
|Count           |db.col.countDocuments({ filter })           |

-----

## Query Operators

|Operator  |Meaning              |Example                         |
|----------|---------------------|--------------------------------|
|$eq       |Equal                |{ price: { $eq: 49.99 } }       |
|$ne       |Not equal            |{ status: { $ne: “CANCELLED” } }|
|$gt       |Greater than         |{ price: { $gt: 100 } }         |
|$gte      |Greater than or equal|{ price: { $gte: 50 } }         |
|$lt       |Less than            |{ price: { $lt: 500 } }         |
|$lte      |Less than or equal   |{ price: { $lte: 200 } }        |
|$in       |In a list            |{ category: { $in: [“A”,“B”] } }|
|$nin      |Not in a list        |{ status: { $nin: [“X”,“Y”] } } |
|$exists   |Field exists         |{ field: { $exists: true } }    |
|$and      |Both true            |{ $and: [{…},{…}] }             |
|$or       |Either true          |{ $or: [{…},{…}] }              |
|$not      |Negate               |{ field: { $not: { $gt: 5 } } } |
|$all      |Array contains all   |{ tags: { $all: [“a”,“b”] } }   |
|$size     |Array has N elements |{ tags: { $size: 3 } }          |
|$elemMatch|Array element matches|{ items: { $elemMatch: {…} } }  |

-----

## Update Operators

|Operator |Meaning                           |
|---------|----------------------------------|
|$set     |Set a field value                 |
|$unset   |Remove a field                    |
|$inc     |Increment a number                |
|$push    |Add item to array                 |
|$pull    |Remove item from array            |
|$addToSet|Add to array if not present       |
|$pop     |Remove first or last array element|
|$rename  |Rename a field                    |

-----

## Aggregation Pipeline Stages

|Stage       |Meaning                            |
|------------|-----------------------------------|
|$match      |Filter documents (like WHERE)      |
|$group      |Group and aggregate (like GROUP BY)|
|$sort       |Sort results (like ORDER BY)       |
|$limit      |Keep first N results               |
|$skip       |Skip first N results               |
|$project    |Select and reshape fields          |
|$lookup     |Join another collection            |
|$unwind     |Deconstruct an array               |
|$count      |Count documents                    |
|$addFields  |Add computed fields                |
|$replaceRoot|Replace document root              |

-----

## Group Accumulators

|Accumulator|Meaning              |
|-----------|---------------------|
|$sum       |Sum of values        |
|$avg       |Average of values    |
|$min       |Minimum value        |
|$max       |Maximum value        |
|$count     |Count of documents   |
|$push      |Collect into array   |
|$addToSet  |Collect unique values|
|$first     |First value in group |
|$last      |Last value in group  |

-----

## Index Types

|Type        |When to Use                              |
|------------|-----------------------------------------|
|Single Field|Filter on one field frequently           |
|Compound    |Filter on multiple fields together       |
|Multikey    |Field contains an array                  |
|Text        |Full text search                         |
|Partial     |Only index documents matching a condition|
|Unique      |Enforce no duplicate values              |

-----

## explain() Output — What to Look For

|Field              |What it means                             |
|-------------------|------------------------------------------|
|stage: COLLSCAN    |No index used — scanning entire collection|
|stage: IXSCAN      |Index used — efficient                    |
|stage: FETCH       |Reading full documents after index lookup |
|totalDocsExamined  |How many documents were scanned           |
|nReturned          |How many documents were returned          |
|executionTimeMillis|How long the query took                   |

**If totalDocsExamined >> nReturned: you need an index.**

-----

## The Three Rules to Always Follow

> **Rule 1:** Design your schema for how the data will be queried,
> not for how it is structured in the source system.

> **Rule 2:** Never store monetary values as floating-point numbers.
> Use NumberDecimal or store as integer cents.

> **Rule 3:** Always use explain() before and after creating an index.
> Never assume an index is being used — verify it.