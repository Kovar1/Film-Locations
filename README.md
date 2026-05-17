# NYC Film Locations Map

An interactive map of 233 film, TV, music video, and commercial shooting locations across New York City. Filter by year, borough, and neighborhood; click a pin to jump to the title's IMDB page.

## View the map

Open `film_locations_map.html` in any modern browser. No server, build step, or install required — everything is self-contained.

## Features

- 233 mapped locations across Manhattan, Brooklyn, Queens, the Bronx, and Staten Island
- Hover a pin to see film title, year, and director
- Click a pin to open its IMDB page in a new tab
- Live filtering:
  - **Year** — single year or range; titles with year ranges in the data (e.g. *Cagney & Lacey*, 1982–1988) match on overlap
  - **Borough** — multi-select
  - **Neighborhood** — multi-select with All / None shortcuts
- A live counter shows how many pins match the current filter

## Regenerate the map

Requires Python 3.9+ and [folium](https://python-visualization.github.io/folium/).

```bash
pip install folium
python generate_map.py
```

This reads `Interactive_Map_Data.xml` and writes `film_locations_map.html` in the same folder.

## Configuration

`generate_map.py` has one config flag at the top:

```python
RESPECT_DISPLAY_FLAG = False
```

Flip to `True` to hide rows where the source data's `Display?` column is not `Y`.

## Files

| File | Purpose |
| --- | --- |
| `Interactive_Map_Data.xml` | Source data (Excel SpreadsheetML format) |
| `generate_map.py` | Builds the map from the XML |
| `film_locations_map.html` | The generated interactive map |

## Data source

`Interactive_Map_Data.xml` is a 2006 Excel SpreadsheetML export accompanying the book *Scenes from the City* (NYC film office dataset). The script reads only a subset of columns: film, year, director, lat/lng, borough, neighborhood, and IMDB link.
https://data.cityofnewyork.us/Business/Filming-Locations-Scenes-from-the-City-/qb3k-n8mm/about_data 
