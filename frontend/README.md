# ShopVerse

React shop for the FastAPI commerce gateway. The static Nginx demo stays at `nginx/static`. This app talks to the same API through a dev-server proxy.

## Run

Start the services first, from the repository root:

```bash
docker compose up
```

Then:

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (usually `http://127.0.0.1:5173`). Requests to `/api` are proxied to `http://127.0.0.1:8080`.

New accounts are shoppers. Admin product and inventory screens appear after you sign in with a token whose `is_admin` claim is true. Promote an account in the user database, then sign in again so the JWT includes that claim.
