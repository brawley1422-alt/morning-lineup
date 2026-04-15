# Morning Lineup — Launch Metrics Dashboard

**Purpose.** Force a daily check-in during launch week so we actually
look at the numbers. Manual fill-in. Read from the Supabase Table
Editor (table: `events`) with the service role.

## How to read the events table

1. Go to [Supabase dashboard](https://xicuxuvuyalpngbhhkpl.supabase.co) → SQL Editor.
2. Run queries below against the `events` table.
3. Paste the counts into the daily log section.
4. The anon key can't read this table — it's write-only from the browser.
   Queries run with the service role when you're signed into the dashboard.

## Core queries

### Total pageviews yesterday
```sql
select count(*) as views
from events
where event_type = 'pageview'
  and created_at >= current_date - interval '1 day'
  and created_at <  current_date;
```

### Pageviews per team (yesterday)
```sql
select team_slug, count(*) as views
from events
where event_type = 'pageview'
  and team_slug is not null
  and created_at >= current_date - interval '1 day'
  and created_at <  current_date
group by team_slug
order by views desc;
```

### Unique sessions (yesterday)
```sql
select count(distinct session_id) as sessions
from events
where event_type = 'pageview'
  and created_at >= current_date - interval '1 day'
  and created_at <  current_date;
```

### Top referrers (last 7 days)
```sql
select referrer, count(*) as hits
from events
where event_type = 'pageview'
  and referrer is not null
  and referrer <> ''
  and created_at >= current_date - interval '7 days'
group by referrer
order by hits desc
limit 20;
```

### Share clicks (when Track D1 ships)
```sql
select team_slug, count(*) as shares
from events
where event_type = 'share_click'
  and created_at >= current_date - interval '7 days'
group by team_slug
order by shares desc;
```

### Install prompt acceptance (when Track D2 ships)
```sql
select
  sum(case when event_type = 'install_shown'    then 1 else 0 end) as shown,
  sum(case when event_type = 'install_accepted' then 1 else 0 end) as accepted,
  sum(case when event_type = 'install_dismissed' then 1 else 0 end) as dismissed
from events
where created_at >= current_date - interval '7 days';
```

### Same-session return rate (proxy for stickiness)
```sql
-- Count sessions that had more than one pageview
with s as (
  select session_id, count(*) as n
  from events
  where event_type = 'pageview'
    and created_at >= current_date - interval '7 days'
  group by session_id
)
select
  count(*)                               as total_sessions,
  sum(case when n >= 2 then 1 else 0 end) as multi_view_sessions,
  round(100.0 * sum(case when n >= 2 then 1 else 0 end) / nullif(count(*), 0), 1) as pct_multi
from s;
```

---

## Daily log

Fill this in every morning during launch week. Skip columns that don't
have data yet (D1/D2 events won't exist until those units ship).

| Date | Views | Uniq Sessions | Top Team | Shares | Install Shown / Accepted | Signups | Notes |
|------|-------|----------------|----------|--------|--------------------------|---------|-------|
| 2026-04-16 | | | | | | | |
| 2026-04-17 | | | | | | | |
| 2026-04-18 | | | | | | | |
| 2026-04-19 | | | | | | | |
| 2026-04-20 | | | | | | | |
| 2026-04-21 | | | | | | | |
| 2026-04-22 | | | | | | | |

## Launch-week targets (from the plan)

- **Shareability:** 100% of team pages render rich OG previews in the FB/Twitter validators. ✅ shipped 2026-04-15
- **SEO:** 30+ pages indexed by Google Search Console within 14 days of launch
- **Conversion:** Cold landing visits that click into a team page ≥ 40%
- **Install:** Mobile visitors who accept the install prompt ≥ 10% of those who see it
- **Retention:** Next-day return rate for installed users ≥ 30%
- **Growth:** Share events per week, tracked by team, non-zero and rising

## Rules of the road

- Don't obsess over day-1 numbers. Look at week-over-week.
- If a team is over-indexing, ask why — did something happen in their game,
  or did the post land somewhere (Reddit, Twitter)?
- If a team is at zero, check that its page is reachable and its OG card
  looks right via the Facebook debugger.
- Keep the log going through launch week + the following week so you can
  separate the launch spike from baseline traffic.

## Schema note

Event rows are never deleted automatically. If the free-tier row count
gets tight, add a nightly `delete from events where created_at < now() -
interval '90 days'` via the Supabase scheduled functions.
