# Storefront API

Contract for the shop UI. Call the gateway only. Do not call service containers or read backend route files.

Base URL: `http://127.0.0.1:8080`

Machine-readable copies of the same contract, exported from the running services:

- `docs/api/user-service.openapi.json`
- `docs/api/product-service.openapi.json`
- `docs/api/order-service.openapi.json`
- `docs/api/inventory-service.openapi.json`

The notification service has no storefront routes. It only exposes `GET /health` inside the Docker network.

## Auth

Protected routes expect:

```http
Authorization: Bearer <access_token>
```

`POST /api/v1/auth/login` returns `access_token` (about 30 minutes) and `refresh_token` (about 7 days). Send the refresh token to `POST /api/v1/auth/refresh` before the access token expires, then replace both tokens.

New accounts are shoppers (`is_admin: false`). Product writes and inventory adjustments require an admin JWT. Customers can read the catalog, place and view their own orders, and cancel those orders.

Passwords must be at least 8 characters and include one uppercase letter, one lowercase letter, and one digit.

Validation failures return `422` with a FastAPI `detail` array. Other errors return `{"detail": "<message>"}`.

## User

### `POST /api/v1/auth/register`

Public. `201` with the created user. `400` if the email is already registered.

```json
{
  "email": "shopper@example.com",
  "first_name": "Ada",
  "last_name": "Lovelace",
  "phone": "+8801...",
  "password": "Secret123"
}
```

`phone` is optional. Response fields: `id`, `email`, `first_name`, `last_name`, `phone`, `is_active`, `is_admin`, `created_at`, `addresses` (empty on create).

### `POST /api/v1/auth/login`

Public. Body is form data, not JSON.

```http
Content-Type: application/x-www-form-urlencoded

username=shopper@example.com&password=Secret123
```

`username` is the email. `200`:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

`401` for a bad email or password. `403` if the account is inactive.

### `POST /api/v1/auth/refresh`

Public. JSON body: `{ "refresh_token": "..." }`. `200` returns a new `access_token` and `refresh_token`. `401` if the refresh token is invalid or the user is gone.

### `GET /api/v1/auth/users/me`

Bearer token. Current profile plus `addresses`.

### `PUT /api/v1/auth/users/me`

Bearer token. Partial JSON: `first_name`, `last_name`, `phone`. Returns the same shape as `GET /me`.

### `PUT /api/v1/auth/users/me/password`

Bearer token.

```json
{
  "current_password": "Secret123",
  "new_password": "Secret456"
}
```

`200`: `{ "message": "Password changed successfully" }`. `400` if the current password is wrong. `new_password` uses the same strength rules as registration.

### Addresses

All require a bearer token. Address object:

| Field | Required | Notes |
| --- | --- | --- |
| `line1` | yes | |
| `line2` | no | |
| `city` | yes | |
| `state` | yes | |
| `postal_code` | yes | |
| `country` | yes | |
| `is_default` | no | defaults to `false`. The first address becomes default even if this is false |

- `GET /api/v1/auth/users/me/addresses` returns an array. Each item also has `id`.
- `POST /api/v1/auth/users/me/addresses` returns `201` and the created address, including `id`.
- `GET /api/v1/auth/users/me/addresses/{address_id}` returns one address. `404` if it is not this user's address.

There is no update or delete address route.

`GET /api/v1/auth/users/{user_id}/verify` is for other services (`X-Service-Token`). The shop UI should not call it.

## Catalog

Product ids are MongoDB ObjectId strings. Read them from `_id`, not `id`.

Product object:

| Field | Type | Notes |
| --- | --- | --- |
| `_id` | string | present on responses |
| `name` | string | |
| `description` | string | |
| `category` | string | |
| `price` | number | must be greater than 0 |
| `quantity` | integer | must be 0 or greater. This is the catalog quantity sent at create time. Live stock is the inventory API |

### `GET /api/v1/products/`

Public. Returns a product array.

Query: `skip` (default 0), `limit` (default 100, max 100), `category`, `name` (case-insensitive contains), `min_price`, `max_price`.

### `GET /api/v1/products/{product_id}`

Public. One product. `400` if the id is not an ObjectId. `404` if missing.

### `GET /api/v1/products/category/list`

Public. Array of category strings, for example `["Electronics"]`.

### Admin writes

Bearer token with `is_admin: true`.

- `POST /api/v1/products/` body is `name`, `description`, `category`, `price`, `quantity`. `201` returns the product. This also creates the inventory row. `503` if inventory could not be created.
- `PUT /api/v1/products/{product_id}` sends only the fields to change. `200` returns the product. `400` if the body is empty or the id is invalid. `404` if missing.
- `DELETE /api/v1/products/{product_id}` returns `204` with an empty body.

## Orders

Bearer token on every order route. A shopper only sees and changes their own orders. Asking for someone else's order returns `404`. Admins can filter and update any order.

Create returns `202`. Stock is reserved by a worker after the response, so poll the order until `reservation_state` leaves `pending`.

`reservation_state`: `pending`, `reserved`, `failed`, `released`.

`status`: `pending`, `paid`, `processing`, `shipped`, `delivered`, `cancelled`, `refunded`.

Allowed status changes:

| From | To |
| --- | --- |
| `pending` | `paid`, `cancelled` |
| `paid` | `processing`, `cancelled`, `refunded` |
| `processing` | `shipped`, `cancelled`, `refunded` |
| `shipped` | `delivered`, `refunded` |
| `delivered` | `refunded` |
| `cancelled` | none |
| `refunded` | none |

Shoppers may only move an order to `cancelled`. Payment is not implemented, so the UI should not send `paid`.

Order response:

| Field | Type |
| --- | --- |
| `_id` | string |
| `user_id` | string (the JWT subject, which is the numeric user id as a string) |
| `items` | `{ product_id, quantity, price }[]` |
| `total_price` | number |
| `status` | string |
| `reservation_state` | string |
| `reserve_attempts` | integer |
| `reservation_expires_at` | ISO datetime or null. Holds last about 15 minutes |
| `shipping_address` | `line1`, optional `line2`, `city`, `state`, `postal_code`, `country` |
| `created_at` | ISO datetime |
| `updated_at` | ISO datetime |

### `POST /api/v1/orders/`

`202`. Header `Idempotency-Key` is required, 8 to 128 characters. Reuse the same key when retrying the same cart. Reusing it with a different body returns `409`.

```http
Authorization: Bearer <access_token>
Idempotency-Key: cart-7f3a9c2e
Content-Type: application/json
```

```json
{
  "items": [
    {
      "product_id": "66f0c2a1b7e4d19a0c11aa22",
      "quantity": 1,
      "price": 699.99
    }
  ],
  "shipping_address": {
    "line1": "12 Road",
    "city": "Dhaka",
    "state": "Dhaka",
    "postal_code": "1205",
    "country": "BD"
  }
}
```

`price` must match the catalog price. `product_id` must be an ObjectId. `quantity` must be at least 1. `400` if the user or a product/price check fails. `503` if the reservation queue is down.

### `GET /api/v1/orders/`

Newest first. Query: `skip` (default 0), `limit` (default 10, max 100), `status`, `user_id` (admin, or the caller's own id), `start_date` and `end_date` as `YYYY-MM-DD`.

### `GET /api/v1/orders/{order_id}`

One order. `400` if the id is not an ObjectId.

### `GET /api/v1/orders/user/{user_id}`

Orders for that user id string. Shoppers must pass their own id. Optional `skip`, `limit`, `status`.

### `PUT /api/v1/orders/{order_id}/status`

```json
{ "status": "cancelled" }
```

`400` if the transition is not allowed. `403` if a shopper sends anything other than `cancelled`. `409` if the row changed concurrently.

### `DELETE /api/v1/orders/{order_id}`

Cancels the order and queues a stock release. `204` empty body. `400` if the order is already `shipped`, `delivered`, `cancelled`, or `refunded`.

## Inventory

Use this for live stock. Catalog `quantity` is not the reserved-stock counter.

Inventory item:

| Field | Type |
| --- | --- |
| `id` | integer |
| `product_id` | string (same ObjectId as the product `_id`) |
| `available_quantity` | integer |
| `reserved_quantity` | integer |
| `reorder_threshold` | integer |
| `created_at` | ISO datetime |
| `updated_at` | ISO datetime |

### `GET /api/v1/inventory/check`

Public. Query `product_id` and `quantity` (integer greater than 0).

Enough stock:

```json
{
  "available": true,
  "current_quantity": 12,
  "requested_quantity": 1,
  "product_id": "66f0c2a1b7e4d19a0c11aa22"
}
```

Unknown product: `available: false` and a `message`, without the quantity fields.

### Bearer routes

- `GET /api/v1/inventory/` query `skip`, `limit` (max 100), `low_stock_only` (`true` or `false`).
- `GET /api/v1/inventory/{product_id}` one item. `404` if that product has no inventory row.
- `GET /api/v1/inventory/low-stock` items at or below their reorder threshold.
- `GET /api/v1/inventory/history/{product_id}` newest first. Query `limit` default 20, max 100. Each row: `id`, `product_id`, `quantity_change`, `previous_quantity`, `new_quantity`, `change_type` (`add`, `remove`, `reserve`, `release`, `update`), `reference_id`, `timestamp`.

### Admin

`POST /api/v1/inventory/adjust` with an admin bearer token.

```json
{
  "product_id": "66f0c2a1b7e4d19a0c11aa22",
  "quantity_change": 5,
  "reason": "Restock",
  "reference_id": null
}
```

`quantity_change` may be negative. `reason` is 3 to 200 characters. Returns the inventory item. `400` if the result would go below zero.

`PUT /api/v1/inventory/{product_id}` is also admin. Optional fields: `available_quantity`, `reserved_quantity`, `reorder_threshold`.

`POST /api/v1/inventory/`, `POST /api/v1/inventory/reserve`, and `POST /api/v1/inventory/release` require the internal `X-Service-Token`. The order worker calls reserve and release. The shop UI should create an order and then read `reservation_state`.

## Gateway health

`GET /health` returns `{ "status": "ok", "service": "api-gateway" }`. Service health checks are not routed through the gateway.
