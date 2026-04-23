from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from .models import FilmRecord


def write_outputs(records: dict[str, FilmRecord], insights: dict, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    films_csv = output_dir / "films_enriched.csv"
    films_json = output_dir / "films_enriched.json"
    insights_json = output_dir / "insights.json"
    insights_html = output_dir / "insights.html"

    _write_films_csv(records, films_csv)
    _write_json([r.as_export_row() for r in records.values()], films_json)
    _write_json(insights, insights_json)
    insights_html.write_text(render_html(insights, records), encoding="utf-8")

    return {
        "films_csv": films_csv,
        "films_json": films_json,
        "insights_json": insights_json,
        "insights_html": insights_html,
    }


def _write_films_csv(records: dict[str, FilmRecord], path: Path) -> None:
    rows = [r.as_export_row() for r in records.values()]
    fieldnames = [
        "film_id",
        "title",
        "year",
        "letterboxd_uri",
        "watch_count",
        "ratings_count",
        "average_rating",
        "genres",
        "directors",
        "actors",
        "runtime_minutes",
        "imdb_id",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(data, path: Path) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def render_html(insights: dict, records: dict | None = None) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary = insights.get("summary", {})

    films_data = []
    if records:
        for r in records.values():
            films_data.append({
                "title": r.title,
                "year": r.year,
                "rating": round(r.average_rating, 1) if r.average_rating is not None else None,
                "watches": r.watch_count,
                "genres": r.metadata.get("genres", []),
                "directors": r.metadata.get("directors", []),
                "actors": r.metadata.get("actors", []),
                "uri": r.letterboxd_uri or "",
            })
    films_json_str = json.dumps(films_data)

    def _chart_data(items: list[dict], key: str = "name", val: str = "count") -> tuple[str, str]:
        labels = json.dumps([str(i.get(key, "")) for i in items])
        values = json.dumps([i.get(val, 0) for i in items])
        return labels, values

    def _film_list(items: list[dict], count_key: str = "watch_count") -> str:
        if not items:
            return "<p class='muted'>No data.</p>"
        rows = ""
        for i, film in enumerate(items, 1):
            title = escape(film.get("title", ""))
            year = film.get("year", "")
            val = film.get(count_key, film.get("ratings_count", ""))
            rows += f"""<div class="film-row">
              <span class="rank">#{i}</span>
              <span class="film-title">{title} <span class="year">({year})</span></span>
              <span class="film-val">{val}</span>
            </div>"""
        return rows

    def _ranked_list(items: list[dict]) -> str:
        if not items:
            return "<p class='muted'>No data.</p>"
        rows = ""
        for i, item in enumerate(items, 1):
            name = escape(str(item.get("name", "")))
            count = item.get("count", 0)
            rows += f"""<div class="film-row">
              <span class="rank">#{i}</span>
              <span class="film-title">{name}</span>
              <span class="film-val">{count}</span>
            </div>"""
        return rows

    # chart data
    rating_labels, rating_values = _chart_data(
        sorted(insights.get("rating_distribution", []), key=lambda x: float(x.get("name", 0)))
    )
    yearly_labels, yearly_values = _chart_data(
        sorted(insights.get("yearly_watch_breakdown", []), key=lambda x: x.get("name", ""))
    )
    monthly_labels, monthly_values = _chart_data(
        sorted(insights.get("monthly_watch_breakdown", [])[:18], key=lambda x: x.get("name", ""))
    )
    decade_labels, decade_values = _chart_data(
        sorted(insights.get("decade_library_breakdown", []), key=lambda x: x.get("name", ""))
    )
    genre_labels, genre_values = _chart_data(insights.get("top_genres", [])[:10])
    director_labels, director_values = _chart_data(insights.get("top_directors", [])[:10])
    actor_labels, actor_values = _chart_data(insights.get("top_actors", [])[:10])

    avg_rating = summary.get("average_rating", 0)
    stars = "★" * round(avg_rating) + "☆" * (5 - round(avg_rating))

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Letterboxd Insights</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    :root {{
      --bg: #14181c;
      --surface: #1c2228;
      --surface2: #242c36;
      --border: #2c3a47;
      --green: #00e054;
      --green-dim: #00b843;
      --text: #e8e0d5;
      --muted: #89a;
      --accent: #40bcf4;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); padding: 2rem 1rem; }}
    .container {{ max-width: 1100px; margin: 0 auto; }}
    header {{ display: flex; align-items: baseline; gap: 1rem; margin-bottom: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 1rem; }}
    header h1 {{ font-size: 1.8rem; color: var(--green); letter-spacing: -0.5px; }}
    header .meta {{ color: var(--muted); font-size: 0.8rem; }}
    .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; margin-bottom: 2.5rem; }}
    .stat-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.2rem 1rem; text-align: center; }}
    .stat-card .val {{ font-size: 2rem; font-weight: 700; color: var(--green); line-height: 1.1; }}
    .stat-card .label {{ font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.3rem; }}
    .stars {{ color: #f5c518; font-size: 1rem; }}
    .section {{ margin-bottom: 2.5rem; }}
    .section h2 {{ font-size: 1rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 1rem; padding-bottom: 0.4rem; border-bottom: 1px solid var(--border); }}
    .chart-wrap {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; }}
    .chart-wrap canvas {{ max-height: 280px; }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
    @media (max-width: 640px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
    .film-row {{ display: flex; align-items: baseline; gap: 0.6rem; padding: 0.5rem 0; border-bottom: 1px solid var(--border); font-size: 0.9rem; }}
    .film-row:last-child {{ border-bottom: none; }}
    .rank {{ color: var(--muted); font-size: 0.75rem; min-width: 1.8rem; }}
    .film-title {{ flex: 1; color: var(--text); }}
    .year {{ color: var(--muted); font-size: 0.8rem; }}
    .film-val {{ color: var(--green); font-weight: 600; font-size: 0.85rem; }}
    .film-list {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1rem 1.25rem; }}
    .muted {{ color: var(--muted); font-size: 0.85rem; padding: 0.5rem 0; }}
  </style>
</head>
<body>
<div class="container">
  <header>
    <h1>Letterboxd Insights</h1>
    <span class="meta">Generated {escape(generated)}</span>
  </header>

  <div class="stat-grid">
    <div class="stat-card"><div class="val">{summary.get('total_films', 0)}</div><div class="label">Unique Films</div></div>
    <div class="stat-card"><div class="val">{summary.get('total_watches', 0)}</div><div class="label">Total Watches</div></div>
    <div class="stat-card"><div class="val">{summary.get('total_ratings', 0)}</div><div class="label">Ratings Given</div></div>
    <div class="stat-card"><div class="val"><span class="stars">{stars}</span><br><span style="font-size:1.1rem">{avg_rating}</span></div><div class="label">Avg Rating</div></div>
    <div class="stat-card"><div class="val">{summary.get('total_runtime_hours', 0):.0f}h</div><div class="label">Total Runtime</div></div>
  </div>

  <div class="section">
    <h2>Rating Distribution</h2>
    <div class="chart-wrap"><canvas id="ratingChart"></canvas></div>
  </div>

  <div class="two-col section">
    <div>
      <h2>Watches by Year</h2>
      <div class="chart-wrap"><canvas id="yearlyChart"></canvas></div>
    </div>
    <div>
      <h2>Films by Decade</h2>
      <div class="chart-wrap"><canvas id="decadeChart"></canvas></div>
    </div>
  </div>

  <div class="section">
    <h2>Monthly Watch Activity</h2>
    <div class="chart-wrap"><canvas id="monthlyChart"></canvas></div>
  </div>

  <div class="two-col section">
    <div>
      <h2>Top Rated Films</h2>
      <div class="film-list">{_film_list(insights.get('top_rated_films', []), count_key='average_rating')}</div>
    </div>
    <div>
      <h2>Most Rewatched</h2>
      <div class="film-list">{_film_list(insights.get('most_rewatched_films', []), count_key='watch_count')}</div>
    </div>
  </div>

  <div class="two-col section">
    <div>
      <h2>Top Directors</h2>
      <div class="film-list">{_ranked_list(insights.get('top_directors', [])[:10])}</div>
    </div>
    <div>
      <h2>Top Actors</h2>
      <div class="film-list">{_ranked_list(insights.get('top_actors', [])[:10])}</div>
    </div>
  </div>

  <div class="section">
    <h2>Top Genres</h2>
    <div class="chart-wrap"><canvas id="genreChart"></canvas></div>
  </div>

  <div class="section" id="search-section">
    <h2>Search &amp; Filter Your Films</h2>
    <div style="display:flex;flex-wrap:wrap;gap:0.6rem;margin-bottom:1rem;">
      <input id="q" type="search" placeholder="Search title, actor, director, genre…"
        style="flex:1;min-width:200px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:0.55rem 0.8rem;color:var(--text);font-size:0.9rem;outline:none;" />
      <select id="f-genre" style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:0.55rem 0.7rem;color:var(--text);font-size:0.85rem;">
        <option value="">All Genres</option>
      </select>
      <select id="f-decade" style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:0.55rem 0.7rem;color:var(--text);font-size:0.85rem;">
        <option value="">All Decades</option>
      </select>
      <select id="f-rating" style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:0.55rem 0.7rem;color:var(--text);font-size:0.85rem;">
        <option value="">Any Rating</option>
        <option value="5">5 stars</option>
        <option value="4.5">4.5+ stars</option>
        <option value="4">4+ stars</option>
        <option value="3.5">3.5+ stars</option>
        <option value="3">3+ stars</option>
      </select>
      <select id="f-sort" style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:0.55rem 0.7rem;color:var(--text);font-size:0.85rem;">
        <option value="rating">Sort: Rating</option>
        <option value="title">Sort: Title</option>
        <option value="year">Sort: Year</option>
        <option value="watches">Sort: Most Watched</option>
      </select>
    </div>
    <div id="search-count" style="font-size:0.8rem;color:var(--muted);margin-bottom:0.6rem;"></div>
    <div id="search-results" style="background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden;"></div>
  </div>

</div>
<script>
  const GRID = {{ color: 'rgba(255,255,255,0.06)' }};
  const TICK = {{ color: '#889aa4', font: {{ size: 11 }} }};
  const GREEN = '#00e054';
  const BLUE = '#40bcf4';
  const defaults = {{
    responsive: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ grid: GRID, ticks: TICK }},
      y: {{ grid: GRID, ticks: TICK, beginAtZero: true }}
    }}
  }};

  new Chart(document.getElementById('ratingChart'), {{
    type: 'bar',
    data: {{ labels: {rating_labels}, datasets: [{{ data: {rating_values}, backgroundColor: GREEN, borderRadius: 6 }}] }},
    options: {{ ...defaults, plugins: {{ ...defaults.plugins, tooltip: {{ callbacks: {{ title: t => t[0].label + ' stars' }} }} }} }}
  }});

  new Chart(document.getElementById('yearlyChart'), {{
    type: 'bar',
    data: {{ labels: {yearly_labels}, datasets: [{{ data: {yearly_values}, backgroundColor: BLUE, borderRadius: 6 }}] }},
    options: defaults
  }});

  new Chart(document.getElementById('decadeChart'), {{
    type: 'bar',
    data: {{ labels: {decade_labels}, datasets: [{{ data: {decade_values}, backgroundColor: '#f5a623', borderRadius: 6 }}] }},
    options: defaults
  }});

  new Chart(document.getElementById('monthlyChart'), {{
    type: 'line',
    data: {{ labels: {monthly_labels}, datasets: [{{ data: {monthly_values}, borderColor: GREEN, backgroundColor: 'rgba(0,224,84,0.1)', fill: true, tension: 0.3, pointBackgroundColor: GREEN, pointRadius: 4 }}] }},
    options: defaults
  }});

  const genreLabels = {genre_labels};
  const genreValues = {genre_values};
  if (genreLabels.length) {{
    new Chart(document.getElementById('genreChart'), {{
      type: 'bar',
      data: {{ labels: genreLabels, datasets: [{{ data: genreValues, backgroundColor: '#9b59b6', borderRadius: 6 }}] }},
      options: {{ ...defaults, indexAxis: 'y', scales: {{ x: {{ grid: GRID, ticks: TICK }}, y: {{ grid: GRID, ticks: {{ ...TICK, font: {{ size: 12 }} }} }} }} }}
    }});
  }} else {{
    document.getElementById('genreChart').parentElement.innerHTML = "<p class='muted' style='padding:1rem'>No genre data — run with --enrich to enable.</p>";
  }}

  // Search & Filter
  const FILMS = {films_json_str};

  // Populate genre + decade dropdowns from data
  const allGenres = [...new Set(FILMS.flatMap(f => f.genres))].sort();
  const allDecades = [...new Set(FILMS.map(f => f.year ? Math.floor(f.year/10)*10 : null).filter(Boolean))].sort();
  const gSel = document.getElementById('f-genre');
  const dSel = document.getElementById('f-decade');
  allGenres.forEach(g => {{ const o = document.createElement('option'); o.value = g; o.textContent = g; gSel.appendChild(o); }});
  allDecades.forEach(d => {{ const o = document.createElement('option'); o.value = d; o.textContent = d + 's'; dSel.appendChild(o); }});

  function stars(r) {{
    if (r === null) return '<span style="color:var(--muted)">—</span>';
    const full = Math.floor(r); const half = r % 1 >= 0.5 ? 1 : 0; const empty = 5 - full - half;
    return '<span style="color:#f5c518;font-size:0.85rem">' + '★'.repeat(full) + (half ? '½' : '') + '</span> <span style="color:var(--muted);font-size:0.8rem">' + r + '</span>';
  }}

  function renderResults(films) {{
    const el = document.getElementById('search-results');
    document.getElementById('search-count').textContent = films.length + ' film' + (films.length !== 1 ? 's' : '');
    if (!films.length) {{ el.innerHTML = '<p style="padding:1rem;color:var(--muted);font-size:0.9rem">No films match.</p>'; return; }}
    el.innerHTML = films.map(f => {{
      const href = f.uri ? `href="${{f.uri}}" target="_blank"` : '';
      const directors = f.directors.length ? '<span style="color:var(--muted);font-size:0.78rem">Dir: ' + f.directors.join(', ') + '</span>' : '';
      const genres = f.genres.length ? '<span style="color:var(--muted);font-size:0.78rem">' + f.genres.slice(0,3).join(' · ') + '</span>' : '';
      const actors = f.actors.length ? '<span style="color:var(--muted);font-size:0.78rem">' + f.actors.slice(0,3).join(', ') + '</span>' : '';
      return `<div style="display:grid;grid-template-columns:1fr auto;gap:0.4rem 1rem;padding:0.65rem 1.2rem;border-bottom:1px solid var(--border);align-items:start;">
        <div>
          <a ${{href}} style="color:var(--text);text-decoration:none;font-size:0.95rem;font-weight:500">${{f.title}}</a>
          <span style="color:var(--muted);font-size:0.8rem;margin-left:0.4rem">${{f.year || ''}}</span>
          ${{f.watches > 1 ? '<span style="background:#1a3a2a;color:var(--green);font-size:0.7rem;padding:0.1rem 0.4rem;border-radius:4px;margin-left:0.4rem">×' + f.watches + '</span>' : ''}}
          <div style="margin-top:0.2rem;display:flex;flex-wrap:wrap;gap:0.4rem">${{directors}}${{genres}}${{actors}}</div>
        </div>
        <div style="text-align:right;white-space:nowrap">${{stars(f.rating)}}</div>
      </div>`;
    }}).join('');
  }}

  function applyFilters() {{
    const q = document.getElementById('q').value.trim().toLowerCase();
    const genre = gSel.value;
    const decade = dSel.value ? parseInt(dSel.value) : null;
    const minRating = parseFloat(document.getElementById('f-rating').value) || null;
    const sort = document.getElementById('f-sort').value;

    let results = FILMS.filter(f => {{
      if (genre && !f.genres.includes(genre)) return false;
      if (decade && (f.year === null || Math.floor(f.year/10)*10 !== decade)) return false;
      if (minRating !== null && (f.rating === null || f.rating < minRating)) return false;
      if (q) {{
        const hay = [f.title, ...f.actors, ...f.directors, ...f.genres].join(' ').toLowerCase();
        if (!q.split(/\\s+/).every(w => hay.includes(w))) return false;
      }}
      return true;
    }});

    results.sort((a, b) => {{
      if (sort === 'title') return a.title.localeCompare(b.title);
      if (sort === 'year') return (b.year || 0) - (a.year || 0);
      if (sort === 'watches') return b.watches - a.watches;
      return (b.rating || 0) - (a.rating || 0);
    }});

    renderResults(results);
  }}

  ['q','f-genre','f-decade','f-rating','f-sort'].forEach(id => document.getElementById(id).addEventListener('input', applyFilters));
  applyFilters();
</script>
</body>
</html>
"""
    return html
