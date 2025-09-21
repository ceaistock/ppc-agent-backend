# PPC Agent - Render Starter (Non-technical guide)

This repo contains a minimal FastAPI app that accepts Google/Meta CSV or Excel exports and inserts normalized rows into a Supabase `ads` table.

## What you need
1. A Supabase project (free): https://supabase.com — create one and open the project settings.
2. In Supabase, create the `ads` table (copy the SQL below).
3. A GitHub account (preferred for Render) or you can upload files directly to Render.
4. A Render account (free tier) to host the backend.

### SQL to create table (run in Supabase SQL editor)
```sql
create table ads (
  id serial primary key,
  date date,
  platform text,
  campaign text,
  adgroup text,
  keyword text,
  impressions bigint,
  clicks bigint,
  cost numeric,
  conversions numeric,
  ctr numeric,
  cpc numeric,
  conv_rate numeric
);
