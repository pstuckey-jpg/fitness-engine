# Fitness + Nutrition Insight Engine

A small local assistant for logging free-form fitness and nutrition notes, storing them in JSON, and generating a concise Daily Advice Brief.

## Project Layout

- `core/` - parsing, storage, entry creation, and brief generation
- `cli/` - minimal command-line interface
- `data/` - local JSON data store
- `web/index.html` - no-install browser app
- `web/app.py` - Flask mobile-friendly web app foundation
- `web/templates/` - route templates
- `web/static/` - mobile-first CSS

## No-Install Browser Version

Open this file in your browser:

```text
web/index.html
```

This version stores entries in your browser's local storage. It does not require Python.

It supports:

- Profile and goal targets: age, sex, height, weight, activity, goal direction, diet preferences, equipment, and injury limits
- Natural meal estimates from common foods, marked as estimates
- Sleep duration from explicit hours or bedtime/wake time
- Workout parsing for entries like `bench 3x8 185`
- Goal-aware advice for lean athletic physique goals, including upper-body emphasis
- Editable previous entries from the recent history list
- 7-day trends for calories, protein, sleep, steps, training frequency, energy, and mood
- Weekly summaries with best day, hardest day, consistency score, trends, and one focus for next week
- Estimated intake guidance for sugar, cholesterol, total fat, saturated fat, caffeine, sodium, and fiber

The browser storage is still local-only, but the entry records include stable IDs, timestamps, and a `user_id` field so the same shape can later move toward accounts, cloud sync, and database-backed storage.

The Python core now uses a `DataStore` abstraction. The default implementation is SQLite at `data/app.db`, with JSON fallback and a cloud database placeholder so PostgreSQL, Supabase, Firebase, PlanetScale, or another hosted database can be added later without rewriting the parser, briefs, trends, weekly summaries, CLI, or web routes.

## Python CLI Commands

Add a daily entry:

```powershell
.\fitness.cmd add
```

Generate the latest brief:

```powershell
.\fitness.cmd brief
```

Generate the weekly summary:

```powershell
.\fitness.cmd weekly
```

Use `.\fitness.cmd ...` on Windows. It tries normal Python first, then the Python launcher, then Codex's bundled Python runtime when available.

If you see `Python was not found`, install Python once, then reopen your terminal:

```powershell
winget install Python.Python.3.12
```

If Python is already available on your system, you can also run the underlying CLI directly:

```powershell
python -m cli.main add
python -m cli.main brief
python -m cli.main weekly
```

## Flask Web Foundation

The server-backed web layer is intentionally minimal. It adds routes for:

- `/signup`
- `/login`
- `/logout`
- `/` daily entry
- `/brief`
- `/history`
- `/weekly`
- `/profile`
- `/settings`
- `/account`

Install the web dependency when you are ready to run the Flask version:

```powershell
pip install -r requirements.txt
flask --app web.app run
```

The current routes use the same `/core` logic as the CLI. They are structured so database-backed storage, sessions, accounts, and future assistant modules can be added without rewriting the route layer.

The Flask layer uses email/password authentication with salted PBKDF2 password hashes. After signup or login, `user_id` is stored in the session and protected routes only show that user's data.

For the quickest synced hosted version, `DEMO_AUTO_LOGIN` defaults to `true`. That means the hosted Flask app automatically uses the shared `demo_user` account, so entries transfer across devices through the server database without requiring login during early testing. Set `DEMO_AUTO_LOGIN=false` later to require signup/login.

SQLite tables are created automatically for:

- `users`
- `profiles`
- `entries`
- `settings`

## Quick Hosted Synced Version

Use the Flask app for account-transfer behavior. The included `render.yaml` and `Procfile` are ready for Render-style hosting:

```text
build: pip install -r requirements.txt
start: gunicorn web.app:app
```

Environment:

```text
DEMO_AUTO_LOGIN=true
SECRET_KEY=<generated secret>
```

This gives you a hosted app where phone and laptop share the same `demo_user` database. For a durable production database, the next step is moving from SQLite-on-server to hosted Postgres/Supabase.

## Quick Hosted Static Version

For the fastest phone-accessible version, deploy the `web` folder as a static site. This uses browser local storage, so each device has its own saved data until the Flask database version is deployed.

Fastest path:

1. Create or log into a Netlify account.
2. Drag the `web` folder into Netlify's deploy drop zone, or connect this repo.
3. If connecting the repo, Netlify can use `netlify.toml`; publish directory is `web` and there is no build command.

This hosted static version includes the current browser app: profile, natural-language entry, editing, daily brief, intake guidance, trends, and weekly summary.

## Example Entry

```text
2026-05-22 push day, 2400 calories, 165g protein, slept 7.5 hours, energy 8/10. Felt strong on bench.
```

The data model is flexible. New parsed fields such as `stress_level`, `mood`, `steps`, `soreness_level`, or `hydration_l` can be added to future records without breaking older entries.
