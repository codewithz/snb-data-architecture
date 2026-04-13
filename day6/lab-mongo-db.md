# Lab 2 — MongoDB Practice Lab
## ShopNoor E-Commerce Platform | Fully Guided
### SNB Data Management Capability Programme

---

> **What this lab is.**
>
> Before applying MongoDB to the Al-Noor Bank domain,
> this lab builds your MongoDB fundamentals in a simpler
> e-commerce context — ShopNoor, Al-Noor Bank's consumer
> retail platform.
>
> You will design documents, insert data, run queries,
> use the aggregation pipeline, and build indexes.
> Every step is explained. Every command is provided.
>
> By the end you will understand embedding vs referencing,
> schema flexibility, the aggregation pipeline, and
> when document modelling is the right choice.
>
> **Time: 60 minutes**

---

## Connection Setup

**Open MongoDB Compass.**
Your connection to `localhost:27017` should already be
listed in the left panel from your earlier setup.

**Click `localhost:27017` to connect.**

If it is not listed:
1. Click **+ Add new connection**
2. Enter: `mongodb://localhost:27017`
3. Click **Connect**

You should see the default databases: admin, config, local.

---

## Part 1 — Understanding the ShopNoor Domain (5 minutes)

ShopNoor is a Saudi e-commerce platform. Customers browse
products, add them to baskets, and place orders. Sellers
manage product listings. Reviews are attached to products.

**Why MongoDB for ShopNoor and not PostgreSQL?**

```
PROBLEM 1: Products have wildly different attributes.
  A mobile phone has: storage, RAM, battery, screen size.
  A T-shirt has: size, colour, material, fit type.
  A food item has: ingredients, allergens, expiry date.

  In PostgreSQL: one enormous table with hundreds of nullable
  columns, or a complex EAV (Entity-Attribute-Value) pattern
  that makes every query painful.

  In MongoDB: each product document contains exactly the
  attributes relevant to that product. Nothing more.

PROBLEM 2: Reviews are embedded in the product context.
  A product review only makes sense in the context of
  the product it reviews. Fetching a product and its reviews
  should be one operation, not a JOIN.

PROBLEM 3: Product catalogue changes constantly.
  New product types require new attributes.
  In PostgreSQL: ALTER TABLE on a 10M-row products table.
  In MongoDB: new documents just have the new field.
  Existing documents are unaffected.
```

---

## Part 2 — Create the Database and Collections (5 minutes)

In MongoDB, databases and collections are created automatically
when you first insert a document. But we will create them
explicitly so you understand the structure.

**In Compass — use the MongoDB Shell tab (bottom of the screen).**
Click the `>_` icon to open the shell.

```javascript
// Switch to (or create) the shopnoor database
use shopnoor

// Verify you are in the right database
db.getName()
// Expected output: 'shopnoor'
```

**Create the collections with schema validation:**

```javascript
// Products collection — with basic validation
db.createCollection("products", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["product_id", "name_en", "name_ar",
                 "category", "seller_id", "price_sar", "status"],
      properties: {
        product_id: { bsonType: "string" },
        name_en:    { bsonType: "string" },
        name_ar:    { bsonType: "string" },
        price_sar:  {
          bsonType: "decimal",
          minimum: 0
        },
        status: {
          enum: ["ACTIVE", "INACTIVE", "OUT_OF_STOCK", "DRAFT"]
        }
      }
    }
  }
})

// Orders collection
db.createCollection("orders")

// Customers collection
db.createCollection("customers")

// Verify collections exist
show collections
// Expected: customers, orders, products
```

---

## Part 3 — Insert Documents (10 minutes)

### 3A — Insert Products

Notice how different product types have completely different
attribute structures. This is the MongoDB advantage.

```javascript
// ── MOBILE PHONES ─────────────────────────────────────────
db.products.insertMany([
  {
    product_id:   "PROD-MOB-001",
    name_en:      "Samsung Galaxy S24 Ultra",
    name_ar:      "سامسونج جالكسي S24 الترا",
    category:     "Electronics",
    subcategory:  "Mobile Phones",
    seller_id:    "SELLER-001",
    seller_name:  "Tech Galaxy Saudi",
    price_sar:    NumberDecimal("4299.00"),
    status:       "ACTIVE",
    stock_qty:    47,
    // Mobile-specific attributes — no other category has these
    specs: {
      storage_gb:    512,
      ram_gb:        12,
      battery_mah:   5000,
      screen_inches: 6.8,
      camera_mp:     200,
      os:            "Android 14",
      color:         "Titanium Black",
      has_5g:        true
    },
    images: [
      "https://cdn.shopnoor.sa/products/mob-001-front.jpg",
      "https://cdn.shopnoor.sa/products/mob-001-back.jpg"
    ],
    // Embedded reviews — read together with product
    reviews: [
      {
        review_id:   "REV-001-001",
        customer_id: "CUST-0001",
        rating:      5,
        title:       "Best phone I have ever owned",
        body:        "Camera quality is exceptional. Battery lasts two full days.",
        verified_purchase: true,
        reviewed_at: new Date("2025-03-15T10:22:00Z"),
        helpful_votes: 34
      },
      {
        review_id:   "REV-001-002",
        customer_id: "CUST-0003",
        rating:      4,
        title:       "Excellent but expensive",
        body:        "Performance is outstanding. Price is steep but justified.",
        verified_purchase: true,
        reviewed_at: new Date("2025-03-28T14:05:00Z"),
        helpful_votes: 18
      }
    ],
    tags: ["smartphone", "samsung", "5g", "flagship"],
    vat_inclusive: true,
    created_at: new Date("2025-01-10T00:00:00Z"),
    updated_at: new Date("2025-03-28T00:00:00Z")
  },

  // ── CLOTHING ──────────────────────────────────────────────
  // Completely different attributes — no specs.storage, no specs.ram
  {
    product_id:   "PROD-CLO-001",
    name_en:      "Classic Thobe - White",
    name_ar:      "ثوب كلاسيكي - أبيض",
    category:     "Clothing",
    subcategory:  "Traditional Wear",
    seller_id:    "SELLER-002",
    seller_name:  "Al-Noor Fashion House",
    price_sar:    NumberDecimal("285.00"),
    status:       "ACTIVE",
    stock_qty:    120,
    // Clothing-specific attributes
    specs: {
      material:    "100% Egyptian Cotton",
      fit:         "Regular",
      collar:      "Mandarin",
      sleeve:      "Full Length",
      care:        "Machine wash cold"
    },
    // Clothing has size variants — mobile phones do not
    variants: [
      { size: "S",   stock: 15, sku: "THO-WHT-S"  },
      { size: "M",   stock: 28, sku: "THO-WHT-M"  },
      { size: "L",   stock: 42, sku: "THO-WHT-L"  },
      { size: "XL",  stock: 25, sku: "THO-WHT-XL" },
      { size: "XXL", stock: 10, sku: "THO-WHT-XXL"}
    ],
    reviews: [
      {
        review_id:   "REV-002-001",
        customer_id: "CUST-0002",
        rating:      5,
        title:       "Perfect quality",
        body:        "Very comfortable fabric. Great for formal occasions.",
        verified_purchase: true,
        reviewed_at: new Date("2025-02-20T09:15:00Z"),
        helpful_votes: 22
      }
    ],
    tags: ["thobe", "traditional", "formal", "cotton"],
    vat_inclusive: true,
    created_at: new Date("2025-01-05T00:00:00Z"),
    updated_at: new Date("2025-02-20T00:00:00Z")
  },

  // ── FOOD ITEMS ────────────────────────────────────────────
  // Completely different again — has allergens, expiry, nutrition
  {
    product_id:   "PROD-FOD-001",
    name_en:      "Premium Saudi Dates - Medjool 1kg",
    name_ar:      "تمر مجدول سعودي فاخر - كيلو",
    category:     "Food & Grocery",
    subcategory:  "Dates & Dry Fruits",
    seller_id:    "SELLER-003",
    seller_name:  "Al-Madinah Date Farm",
    price_sar:    NumberDecimal("89.00"),
    status:       "ACTIVE",
    stock_qty:    350,
    // Food-specific attributes
    specs: {
      weight_kg:   1.0,
      origin:      "Al-Madinah Al-Munawwarah",
      variety:     "Medjool",
      organic:     true,
      shelf_life_days: 180
    },
    // Food has nutrition and allergens — no other category does
    nutrition_per_100g: {
      calories:      277,
      carbohydrates: 75,
      sugar:         63.4,
      fibre:         6.7,
      protein:       1.8,
      fat:           0.2
    },
    allergens: [],   // None — pure dates
    halal_certified: true,
    reviews: [
      {
        review_id:   "REV-003-001",
        customer_id: "CUST-0004",
        rating:      5,
        title:       "The best dates I have ever tasted",
        body:        "Soft, sweet, and perfectly fresh. Will reorder.",
        verified_purchase: true,
        reviewed_at: new Date("2025-04-01T11:30:00Z"),
        helpful_votes: 67
      },
      {
        review_id:   "REV-003-002",
        customer_id: "CUST-0001",
        rating:      4,
        title:       "Excellent quality, fast delivery",
        body:        "Great product. Arrived well-packaged.",
        verified_purchase: true,
        reviewed_at: new Date("2025-04-05T08:45:00Z"),
        helpful_votes: 29
      }
    ],
    tags: ["dates", "medjool", "organic", "halal", "gift"],
    vat_inclusive: false,  // Food is VAT-exempt in Saudi Arabia
    created_at: new Date("2025-02-01T00:00:00Z"),
    updated_at: new Date("2025-04-05T00:00:00Z")
  },

  // ── OUT OF STOCK PRODUCT ──────────────────────────────────
  {
    product_id:   "PROD-MOB-002",
    name_en:      "Apple iPhone 16 Pro - 256GB",
    name_ar:      "آبل آيفون 16 برو - 256 جيجا",
    category:     "Electronics",
    subcategory:  "Mobile Phones",
    seller_id:    "SELLER-001",
    seller_name:  "Tech Galaxy Saudi",
    price_sar:    NumberDecimal("4799.00"),
    status:       "OUT_OF_STOCK",
    stock_qty:    0,
    specs: {
      storage_gb:    256,
      ram_gb:        8,
      battery_mah:   3274,
      screen_inches: 6.3,
      camera_mp:     48,
      os:            "iOS 18",
      color:         "Desert Titanium",
      has_5g:        true
    },
    reviews: [],
    tags: ["iphone", "apple", "flagship", "ios"],
    vat_inclusive: true,
    created_at: new Date("2025-03-01T00:00:00Z"),
    updated_at: new Date("2025-04-10T00:00:00Z")
  }
])
```

### 3B — Insert Customers

```javascript
db.customers.insertMany([
  {
    customer_id:    "CUST-0001",
    name_en:        "Ahmed Al-Omari",
    name_ar:        "أحمد العمري",
    email:          "ahmed.omari@email.com",
    mobile:         "+966501234567",
    segment:        "PREMIUM",
    registered_at:  new Date("2023-06-15T00:00:00Z"),
    addresses: [
      {
        type:       "HOME",
        city:       "Riyadh",
        district:   "Al Olaya",
        street:     "King Fahd Road",
        is_default: true
      },
      {
        type:       "WORK",
        city:       "Riyadh",
        district:   "Al Malaz",
        street:     "Prince Turki Street",
        is_default: false
      }
    ],
    preferences: {
      language:       "ar",
      currency:       "SAR",
      notifications:  ["sms", "email"]
    }
  },
  {
    customer_id:    "CUST-0002",
    name_en:        "Fatima Al-Zahrani",
    name_ar:        "فاطمة الزهراني",
    email:          "f.zahrani@email.com",
    mobile:         "+966509876543",
    segment:        "STANDARD",
    registered_at:  new Date("2024-01-22T00:00:00Z"),
    addresses: [
      {
        type:       "HOME",
        city:       "Jeddah",
        district:   "Al Rawdah",
        street:     "Palestine Street",
        is_default: true
      }
    ],
    preferences: {
      language:       "ar",
      currency:       "SAR",
      notifications:  ["email"]
    }
  },
  {
    customer_id:    "CUST-0003",
    name_en:        "Khalid Al-Qahtani",
    name_ar:        "خالد القحطاني",
    email:          "k.qahtani@email.com",
    mobile:         "+966505555555",
    segment:        "PREMIUM",
    registered_at:  new Date("2022-11-08T00:00:00Z"),
    addresses: [
      {
        type:       "HOME",
        city:       "Riyadh",
        district:   "Al Nakheel",
        street:     "Northern Ring Road",
        is_default: true
      }
    ],
    preferences: {
      language:       "en",
      currency:       "SAR",
      notifications:  ["sms"]
    }
  },
  {
    customer_id:    "CUST-0004",
    name_en:        "Noura Al-Saeed",
    name_ar:        "نورة السعيد",
    email:          "n.saeed@email.com",
    mobile:         "+966503334444",
    segment:        "STANDARD",
    registered_at:  new Date("2024-03-10T00:00:00Z"),
    addresses: [
      {
        type:       "HOME",
        city:       "Dammam",
        district:   "Al Shati",
        street:     "King Abdullah Road",
        is_default: true
      }
    ],
    preferences: {
      language:       "ar",
      currency:       "SAR",
      notifications:  ["sms", "email", "push"]
    }
  }
])
```

### 3C — Insert Orders

```javascript
db.orders.insertMany([
  {
    order_id:       "ORD-2025-0001",
    customer_id:    "CUST-0001",
    customer_name:  "Ahmed Al-Omari",
    order_date:     new Date("2025-04-10T14:33:00Z"),
    status:         "DELIVERED",
    channel:        "MOBILE_APP",
    shipping_address: {
      city:     "Riyadh",
      district: "Al Olaya",
      street:   "King Fahd Road"
    },
    items: [
      {
        product_id:   "PROD-MOB-001",
        product_name: "Samsung Galaxy S24 Ultra",
        quantity:     1,
        unit_price:   NumberDecimal("4299.00"),
        vat_amount:   NumberDecimal("644.85"),
        line_total:   NumberDecimal("4299.00")
      },
      {
        product_id:   "PROD-FOD-001",
        product_name: "Premium Saudi Dates - Medjool 1kg",
        quantity:     2,
        unit_price:   NumberDecimal("89.00"),
        vat_amount:   NumberDecimal("0.00"),
        line_total:   NumberDecimal("178.00")
      }
    ],
    payment: {
      method:         "MADA",
      amount_sar:     NumberDecimal("4477.00"),
      vat_total:      NumberDecimal("644.85"),
      status:         "CAPTURED",
      transaction_ref:"MADA-REF-20250410-0041"
    },
    delivery: {
      carrier:        "Aramex",
      tracking_no:    "ARX-SA-2025-884421",
      estimated_date: new Date("2025-04-12T00:00:00Z"),
      delivered_at:   new Date("2025-04-12T10:15:00Z")
    },
    subtotal_sar:   NumberDecimal("4477.00"),
    vat_total:      NumberDecimal("644.85"),
    shipping_fee:   NumberDecimal("0.00"),
    order_total:    NumberDecimal("4477.00"),
    created_at:     new Date("2025-04-10T14:33:00Z")
  },

  {
    order_id:       "ORD-2025-0002",
    customer_id:    "CUST-0002",
    customer_name:  "Fatima Al-Zahrani",
    order_date:     new Date("2025-04-11T09:15:00Z"),
    status:         "PROCESSING",
    channel:        "WEBSITE",
    shipping_address: {
      city:     "Jeddah",
      district: "Al Rawdah",
      street:   "Palestine Street"
    },
    items: [
      {
        product_id:   "PROD-CLO-001",
        product_name: "Classic Thobe - White",
        quantity:     2,
        unit_price:   NumberDecimal("285.00"),
        variant:      { size: "L" },
        vat_amount:   NumberDecimal("85.50"),
        line_total:   NumberDecimal("570.00")
      }
    ],
    payment: {
      method:         "VISA",
      amount_sar:     NumberDecimal("570.00"),
      vat_total:      NumberDecimal("85.50"),
      status:         "CAPTURED",
      transaction_ref:"VISA-REF-20250411-0017"
    },
    delivery: {
      carrier:        "SMSA",
      tracking_no:    "SMSA-SA-2025-336622",
      estimated_date: new Date("2025-04-14T00:00:00Z"),
      delivered_at:   null
    },
    subtotal_sar:   NumberDecimal("570.00"),
    vat_total:      NumberDecimal("85.50"),
    shipping_fee:   NumberDecimal("25.00"),
    order_total:    NumberDecimal("595.00"),
    created_at:     new Date("2025-04-11T09:15:00Z")
  },

  {
    order_id:       "ORD-2025-0003",
    customer_id:    "CUST-0001",
    customer_name:  "Ahmed Al-Omari",
    order_date:     new Date("2025-04-12T20:44:00Z"),
    status:         "PENDING",
    channel:        "MOBILE_APP",
    shipping_address: {
      city:     "Riyadh",
      district: "Al Olaya",
      street:   "King Fahd Road"
    },
    items: [
      {
        product_id:   "PROD-FOD-001",
        product_name: "Premium Saudi Dates - Medjool 1kg",
        quantity:     5,
        unit_price:   NumberDecimal("89.00"),
        vat_amount:   NumberDecimal("0.00"),
        line_total:   NumberDecimal("445.00")
      }
    ],
    payment: {
      method:         "STCPAY",
      amount_sar:     NumberDecimal("445.00"),
      vat_total:      NumberDecimal("0.00"),
      status:         "PENDING",
      transaction_ref: null
    },
    subtotal_sar:   NumberDecimal("445.00"),
    vat_total:      NumberDecimal("0.00"),
    shipping_fee:   NumberDecimal("0.00"),
    order_total:    NumberDecimal("445.00"),
    created_at:     new Date("2025-04-12T20:44:00Z")
  }
])
```

**Verify your inserts:**
```javascript
db.products.countDocuments()   // Expected: 4
db.customers.countDocuments()  // Expected: 4
db.orders.countDocuments()     // Expected: 3
```

---

## Part 4 — Querying Documents (15 minutes)

### Query 1 — Find all active products

```javascript
db.products.find(
  { status: "ACTIVE" },
  { product_id: 1, name_en: 1, price_sar: 1, category: 1, _id: 0 }
)

// The second argument is the projection — which fields to return.
// 1 = include,  0 = exclude.
// _id: 0 excludes the MongoDB internal ID from results.
```

---

### Query 2 — Find products in a price range

```javascript
// Products between SAR 100 and SAR 500
db.products.find(
  {
    price_sar: {
      $gte: NumberDecimal("100"),
      $lte: NumberDecimal("500")
    },
    status: "ACTIVE"
  },
  { product_id: 1, name_en: 1, price_sar: 1, category: 1, _id: 0 }
).sort({ price_sar: 1 })
```

---

### Query 3 — Find products with a specific tag

```javascript
// The $in operator searches inside arrays
db.products.find(
  { tags: { $in: ["5g", "flagship"] } },
  { product_id: 1, name_en: 1, tags: 1, _id: 0 }
)
```

---

### Query 4 — Find products with at least one 5-star review

```javascript
// Querying into embedded arrays with dot notation
db.products.find(
  { "reviews.rating": 5 },
  { product_id: 1, name_en: 1, "reviews.rating": 1, _id: 0 }
)
```

---

### Query 5 — Find a specific review by review_id

```javascript
// elemMatch: find document where at least one
// array element matches ALL conditions
db.products.find(
  {
    reviews: {
      $elemMatch: {
        review_id: "REV-001-001",
        rating: { $gte: 4 }
      }
    }
  },
  { product_id: 1, name_en: 1, _id: 0 }
)
```

---

### Query 6 — Find all orders for a specific customer

```javascript
db.orders.find(
  { customer_id: "CUST-0001" },
  {
    order_id: 1,
    order_date: 1,
    status: 1,
    order_total: 1,
    _id: 0
  }
).sort({ order_date: -1 })

// -1 = descending (newest first)
// +1 = ascending (oldest first)
```

---

### Query 7 — Find orders containing a specific product

```javascript
// Searching inside the items array in each order
db.orders.find(
  { "items.product_id": "PROD-FOD-001" },
  {
    order_id: 1,
    customer_id: 1,
    order_date: 1,
    status: 1,
    _id: 0
  }
)
// Expected: ORD-2025-0001 and ORD-2025-0003
// Both orders contain the dates product
```

---

### Query 8 — Find orders with VAT-exempt items and PENDING payment

```javascript
db.orders.find(
  {
    "payment.status": "PENDING",
    "items.vat_amount": NumberDecimal("0.00")
  },
  {
    order_id: 1,
    "payment.method": 1,
    "payment.status": 1,
    order_total: 1,
    _id: 0
  }
)
```

---

## Part 5 — Update Operations (5 minutes)

### Update 1 — Update stock quantity when a sale occurs

```javascript
// An order just came in for 2 units of the Thobe
db.products.updateOne(
  { product_id: "PROD-CLO-001" },
  {
    $inc: { stock_qty: -2 },      // decrement by 2
    $set: { updated_at: new Date() }
  }
)

// Verify the update
db.products.findOne(
  { product_id: "PROD-CLO-001" },
  { product_id: 1, stock_qty: 1, status: 1, _id: 0 }
)
// stock_qty should now be 118 (was 120)
```

---

### Update 2 — Add a new review to a product

```javascript
// A customer just submitted a new review — push it to the array
db.products.updateOne(
  { product_id: "PROD-CLO-001" },
  {
    $push: {
      reviews: {
        review_id:         "REV-002-002",
        customer_id:       "CUST-0004",
        rating:            5,
        title:             "Beautiful quality, will buy again",
        body:              "The fabric is breathable and feels premium.",
        verified_purchase: true,
        reviewed_at:       new Date("2025-04-12T16:30:00Z"),
        helpful_votes:     0
      }
    },
    $set: { updated_at: new Date() }
  }
)

// Verify: should now have 2 reviews
db.products.findOne(
  { product_id: "PROD-CLO-001" },
  { product_id: 1, "reviews.review_id": 1, _id: 0 }
)
```

---

### Update 3 — Mark an order as delivered

```javascript
db.orders.updateOne(
  { order_id: "ORD-2025-0002" },
  {
    $set: {
      status: "DELIVERED",
      "delivery.delivered_at": new Date("2025-04-14T11:30:00Z"),
      "payment.status": "SETTLED"
    }
  }
)
```

---

## Part 6 — The Aggregation Pipeline (15 minutes)

The aggregation pipeline is MongoDB's power tool for analytics.
Each stage transforms the documents and passes them to the next.

```
Collection → [$match] → [$group] → [$sort] → [$project] → Result
```

### Pipeline 1 — Total sales by category

```javascript
db.orders.aggregate([
  // Stage 1: Only completed/delivered orders
  {
    $match: {
      status: { $in: ["DELIVERED", "PROCESSING"] }
    }
  },

  // Stage 2: Unwind the items array
  // Creates one document per item (one order with 3 items → 3 documents)
  { $unwind: "$items" },

  // Stage 3: Join with products to get category
  {
    $lookup: {
      from:         "products",
      localField:   "items.product_id",
      foreignField: "product_id",
      as:           "product_info"
    }
  },

  // Stage 4: Flatten the product_info array (always 1 element)
  { $unwind: "$product_info" },

  // Stage 5: Group by category and sum revenue
  {
    $group: {
      _id:           "$product_info.category",
      total_revenue: { $sum: "$items.line_total" },
      total_items:   { $sum: "$items.quantity" },
      order_count:   { $sum: 1 }
    }
  },

  // Stage 6: Sort by revenue descending
  { $sort: { total_revenue: -1 } },

  // Stage 7: Clean up output field names
  {
    $project: {
      _id:           0,
      category:      "$_id",
      total_revenue: 1,
      total_items:   1,
      order_count:   1
    }
  }
])
```

---

### Pipeline 2 — Average rating per product

```javascript
db.products.aggregate([
  // Stage 1: Only products with reviews
  { $match: { "reviews.0": { $exists: true } } },

  // Stage 2: Unwind reviews
  { $unwind: "$reviews" },

  // Stage 3: Group by product, calculate average rating
  {
    $group: {
      _id:            "$product_id",
      product_name:   { $first: "$name_en" },
      avg_rating:     { $avg: "$reviews.rating" },
      review_count:   { $sum: 1 },
      total_votes:    { $sum: "$reviews.helpful_votes" }
    }
  },

  // Stage 4: Round the average rating to 1 decimal
  {
    $addFields: {
      avg_rating: { $round: ["$avg_rating", 1] }
    }
  },

  // Stage 5: Sort by average rating descending
  { $sort: { avg_rating: -1, review_count: -1 } },

  {
    $project: {
      _id:          0,
      product_id:   "$_id",
      product_name: 1,
      avg_rating:   1,
      review_count: 1,
      total_votes:  1
    }
  }
])
```

---

### Pipeline 3 — Customer spending summary (PREMIUM vs STANDARD)

```javascript
db.orders.aggregate([
  // Stage 1: Only completed orders
  { $match: { status: "DELIVERED" } },

  // Stage 2: Join with customers to get segment
  {
    $lookup: {
      from:         "customers",
      localField:   "customer_id",
      foreignField: "customer_id",
      as:           "customer_info"
    }
  },

  { $unwind: "$customer_info" },

  // Stage 3: Group by segment
  {
    $group: {
      _id:             "$customer_info.segment",
      total_revenue:   { $sum: "$order_total" },
      order_count:     { $sum: 1 },
      avg_order_value: { $avg: "$order_total" },
      unique_customers: { $addToSet: "$customer_id" }
    }
  },

  {
    $addFields: {
      customer_count: { $size: "$unique_customers" }
    }
  },

  {
    $project: {
      _id:             0,
      segment:         "$_id",
      total_revenue:   1,
      order_count:     1,
      avg_order_value: { $round: ["$avg_order_value", 2] },
      customer_count:  1
    }
  },

  { $sort: { total_revenue: -1 } }
])
```

---

### Pipeline 4 — Out of stock products with recent order history

```javascript
// Which products are out of stock but customers are still trying to order?
db.products.aggregate([
  // Stage 1: Out of stock products only
  { $match: { status: "OUT_OF_STOCK" } },

  // Stage 2: Check if any orders contain this product
  {
    $lookup: {
      from:         "orders",
      localField:   "product_id",
      foreignField: "items.product_id",
      as:           "recent_orders"
    }
  },

  {
    $project: {
      _id:          0,
      product_id:   1,
      name_en:      1,
      price_sar:    1,
      stock_qty:    1,
      demand_count: { $size: "$recent_orders" }
    }
  },

  { $sort: { demand_count: -1 } }
])
// If demand_count > 0: restock priority
```

---

## Part 7 — Indexes (5 minutes)

Without indexes, MongoDB does a full collection scan for every query.
With indexes, it finds documents directly.

```javascript
// ── Check current indexes ──────────────────────────────────
db.products.getIndexes()
// You will see _id index only — the default

// ── Create indexes ─────────────────────────────────────────

// Index 1: Products by category and status
// Serves: "show me all active Electronics"
db.products.createIndex(
  { category: 1, status: 1 },
  { name: "idx_products_category_status" }
)

// Index 2: Products by price range
// Serves: "show me products between SAR 100 and SAR 500"
db.products.createIndex(
  { price_sar: 1 },
  { name: "idx_products_price" }
)

// Index 3: Products by tag (multikey index — array field)
// Serves: find({tags: {$in: ["5g", "flagship"]}})
db.products.createIndex(
  { tags: 1 },
  { name: "idx_products_tags" }
)

// Index 4: Orders by customer (most frequent query pattern)
db.orders.createIndex(
  { customer_id: 1, order_date: -1 },
  { name: "idx_orders_customer_date" }
)

// Index 5: Orders by status (operations dashboard)
db.orders.createIndex(
  { status: 1 },
  { name: "idx_orders_status" }
)

// ── Verify all indexes ─────────────────────────────────────
db.products.getIndexes()
// Should now show 4 indexes (including _id)

db.orders.getIndexes()
// Should show 3 indexes (including _id)
```

**Check if a query uses an index (explain plan):**

```javascript
// Does our category query use the index?
db.products.find(
  { category: "Electronics", status: "ACTIVE" }
).explain("executionStats")

// Look for:
// "stage": "IXSCAN"   ← index scan (good — uses index)
// "stage": "COLLSCAN" ← collection scan (bad — no index used)
// "nReturned" vs "totalDocsExamined" — should be equal or close
```

---

## Part 8 — Compass GUI Exploration (5 minutes)

Use Compass to explore what you built visually.

**Navigate in Compass:**
1. Click `shopnoor` in the left panel
2. Click `products` collection
3. Click **Documents** tab — browse all four products
4. Notice how each document has different fields — the dates
   product has `nutrition_per_100g`, the phone has `specs.ram_gb`,
   the clothing has `variants`. This is schema flexibility.

**Run a query in the Compass filter bar:**
```
{ "status": "ACTIVE", "category": "Electronics" }
```

**Use the Aggregations tab:**
1. Click the **Aggregations** tab
2. Add a `$match` stage: `{ status: "ACTIVE" }`
3. Add a `$project` stage: `{ name_en: 1, price_sar: 1, category: 1, _id: 0 }`
4. Click **Run** — see results update in real time

**Check Indexes tab:**
Click the **Indexes** tab on the products collection.
You should see all four indexes you created.
The `_id` index was automatic. The other three were yours.

---

## Lab Complete — What You Built

```
✓ shopnoor database with 3 collections
✓ Schema validation on the products collection
✓ 4 products with completely different attribute structures
  demonstrating MongoDB's schema flexibility
✓ 4 customers with embedded address arrays
✓ 3 orders with embedded items, payment, and delivery
✓ 8 queries covering: exact match, range, array search,
  nested field search, elemMatch
✓ 3 update operations: $inc, $push, $set with dot notation
✓ 4 aggregation pipelines covering: $match, $unwind,
  $lookup (JOIN equivalent), $group, $sort, $project
✓ 5 indexes with explain plan verification
✓ Compass GUI exploration of documents and aggregations
```

**Key concepts demonstrated:**

```
EMBEDDING vs REFERENCING:
  Reviews are embedded in products — read together, always.
  Orders reference customers by customer_id — not embedded.
  Why? A customer document should not contain their entire
  order history (unbounded growth). Orders reference customer.
  Reviews are bounded — a product has a manageable number.
  Reviews belong with the product.

SCHEMA FLEXIBILITY:
  Four products, four different structures.
  No ALTER TABLE. No NULL columns. No schema migration.
  Each document contains exactly what it needs.

AGGREGATION PIPELINE:
  $lookup is MongoDB's JOIN equivalent.
  $unwind flattens arrays for grouping.
  Pipelines are composable — each stage feeds the next.
```

---

*SNB Data Management Capability Programme | Delivered by Fitch Learning*