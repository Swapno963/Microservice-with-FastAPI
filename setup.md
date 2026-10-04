For creating a superuser:
docker compose exec postgres-user psql -U postgres -d user_db -c \
  "UPDATE users SET is_admin = TRUE WHERE email = 'a@g.com';"
UPDATE 1