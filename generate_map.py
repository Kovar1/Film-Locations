"""Generate an interactive NYC film locations map from the XML data."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from string import Template

import folium

# Set True to hide rows where Display? is not 'Y'.
RESPECT_DISPLAY_FLAG = False

HERE = Path(__file__).parent
XML_PATH = HERE / "Interactive_Map_Data.xml"
OUTPUT_PATH = HERE / "film_locations_map.html"

# SpreadsheetML namespace, used for findall() lookups and Clark-notation attribute names.
NS = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}
SS = "{" + NS["ss"] + "}"

# 1-based column indexes in the "Full Map List" sheet.
COL_FILM = 1
COL_YEAR = 2
COL_DIRECTOR = 7
COL_LAT = 10
COL_LNG = 11
COL_BOROUGH = 12
COL_NEIGHBORHOOD = 13
COL_IMDB = 16
COL_DISPLAY = 21


# ----- parsing -------------------------------------------------------------

def iter_rows(xml_path):
    """Yield each Row in 'Full Map List' as {col_index: cell_text_or_None}."""
    root = ET.parse(xml_path).getroot()
    sheet = next(
        ws for ws in root.findall("ss:Worksheet", NS)
        if ws.get(SS + "Name") == "Full Map List"
    )
    for row in sheet.find("ss:Table", NS).findall("ss:Row", NS):
        cells = {}
        col = 1
        for cell in row.findall("ss:Cell", NS):
            # ss:Index lets a cell jump to a non-sequential column.
            idx = cell.get(SS + "Index")
            if idx:
                col = int(idx)
            data = cell.find("ss:Data", NS)
            cells[col] = data.text if data is not None else None
            col += 1
        yield cells


def cell_text(cells, col):
    return (cells.get(col) or "").strip()


def year_bounds(year):
    """'1958-1963' -> (1958, 1963); '1987' -> (1987, 1987); unparseable -> (None, None)."""
    if not year:
        return None, None
    if "-" in year:
        a, _, b = year.partition("-")
        try:
            return int(a.strip()), int(b.strip())
        except ValueError:
            return None, None
    try:
        v = int(float(year))
        return v, v
    except ValueError:
        return None, None


def build_records():
    records = []
    for cells in iter_rows(XML_PATH):
        film = cell_text(cells, COL_FILM)
        if not film:
            continue
        try:
            lat = float(cells.get(COL_LAT))
            lng = float(cells.get(COL_LNG))
        except (TypeError, ValueError):
            continue
        if RESPECT_DISPLAY_FLAG and cell_text(cells, COL_DISPLAY).upper() != "Y":
            continue

        year = cell_text(cells, COL_YEAR)
        y_min, y_max = year_bounds(year)
        records.append({
            "film": film,
            "year": year,
            "yMin": y_min,
            "yMax": y_max,
            "director": cell_text(cells, COL_DIRECTOR),
            "lat": lat,
            "lng": lng,
            "borough": cell_text(cells, COL_BOROUGH),
            "neighborhood": cell_text(cells, COL_NEIGHBORHOOD),
            "imdb": cell_text(cells, COL_IMDB),
        })
    return records


# ----- rendering -----------------------------------------------------------

def checkbox_html(name, values):
    return "".join(
        f'<label style="display:block;"><input type="checkbox" name="{name}" value="{v}" checked> {v}</label>'
        for v in values
    )


PANEL_TEMPLATE = Template("""
<div id="filter-panel" style="position: fixed; top: 10px; right: 10px; z-index: 9999;
     background: white; padding: 12px; border: 1px solid #ccc; border-radius: 6px;
     max-height: 92vh; overflow-y: auto; width: 270px; font-family: sans-serif; font-size: 13px;
     box-shadow: 0 2px 8px rgba(0,0,0,0.2);">
    <h3 style="margin: 0 0 6px 0; font-size: 15px;">Filters</h3>
    <div id="match-count" style="margin-bottom: 10px; color: #555; font-size: 12px;"></div>

    <div style="margin-bottom: 10px;">
        <strong>Year</strong>
        <div style="margin-top: 4px;">
            <label>From <input id="yearFrom" type="number" style="width: 70px;"></label>
            <label style="margin-left: 4px;">To <input id="yearTo" type="number" style="width: 70px;"></label>
        </div>
        <div style="font-size: 11px; color: #888; margin-top: 2px;">
            Enter the same value in both for a single year. Leave blank for no limit.
        </div>
    </div>

    <details open style="margin-bottom: 8px;">
        <summary><strong>Borough</strong></summary>
        <div style="margin-top: 4px;">
            <button type="button" onclick="toggleAll('borough', true)">All</button>
            <button type="button" onclick="toggleAll('borough', false)">None</button>
            <div style="margin-top: 4px;">$borough_html</div>
        </div>
    </details>

    <details style="margin-bottom: 4px;">
        <summary><strong>Neighborhood</strong></summary>
        <div style="margin-top: 4px;">
            <button type="button" onclick="toggleAll('neighborhood', true)">All</button>
            <button type="button" onclick="toggleAll('neighborhood', false)">None</button>
            <div style="max-height: 220px; overflow-y: auto; margin-top: 4px; border: 1px solid #eee; padding: 4px;">
                $neighborhood_html
            </div>
        </div>
    </details>
</div>
""")

# Runs on DOMContentLoaded so folium's L.map() (in the same <script> block) has executed first.
SCRIPT_TEMPLATE = Template("""
document.addEventListener('DOMContentLoaded', function() {
    var ALL_RECORDS = $data_json;
    var markerLayer = L.layerGroup().addTo($map_var);

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, function(c) {
            return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c];
        });
    }

    function suffix(r) {
        var s = '';
        if (r.year)     s += ' (' + escapeHtml(r.year) + ')';
        if (r.director) s += '<br><small>' + escapeHtml(r.director) + '</small>';
        return s;
    }

    function render(records) {
        markerLayer.clearLayers();
        records.forEach(function(r) {
            var title = '<strong>' + escapeHtml(r.film) + '</strong>';
            var link  = r.imdb
                ? '<a href="' + escapeHtml(r.imdb) + '" target="_blank" rel="noopener">' + title + '</a>'
                : title;
            L.marker([r.lat, r.lng])
                .bindTooltip(title + suffix(r), {direction: 'top', offset: [0, -10]})
                .bindPopup(link + suffix(r))
                .addTo(markerLayer);
        });
        document.getElementById('match-count').textContent =
            'Showing ' + records.length + ' of ' + ALL_RECORDS.length + ' locations';
    }

    function getChecked(name) {
        return Array.prototype.slice.call(
            document.querySelectorAll('input[name="' + name + '"]:checked')
        ).map(function(c) { return c.value; });
    }

    function applyFilters() {
        var yf = parseInt(document.getElementById('yearFrom').value, 10);
        var yt = parseInt(document.getElementById('yearTo').value, 10);
        if (isNaN(yf)) yf = -Infinity;
        if (isNaN(yt)) yt =  Infinity;
        var boroughs = getChecked('borough');
        var neighborhoods = getChecked('neighborhood');

        render(ALL_RECORDS.filter(function(r) {
            // Year ranges overlap-match; rows with no parseable year always pass.
            if (r.yMin != null && (r.yMax < yf || r.yMin > yt)) return false;
            if (r.borough && boroughs.indexOf(r.borough) === -1) return false;
            if (r.neighborhood && neighborhoods.indexOf(r.neighborhood) === -1) return false;
            return true;
        }));
    }

    window.toggleAll = function(name, checked) {
        document.querySelectorAll('input[name="' + name + '"]').forEach(function(c) {
            c.checked = checked;
        });
        applyFilters();
    };

    document.addEventListener('change', function(e) {
        if (e.target.matches('#yearFrom, #yearTo, input[name="borough"], input[name="neighborhood"]')) {
            applyFilters();
        }
    });

    render(ALL_RECORDS);
});
""")


def build_map(records):
    m = folium.Map(location=[40.7128, -74.0060], zoom_start=11, tiles="cartodbpositron")

    boroughs = sorted({r["borough"] for r in records if r["borough"]})
    neighborhoods = sorted({r["neighborhood"] for r in records if r["neighborhood"]})

    panel_html = PANEL_TEMPLATE.substitute(
        borough_html=checkbox_html("borough", boroughs),
        neighborhood_html=checkbox_html("neighborhood", neighborhoods),
    )
    script_js = SCRIPT_TEMPLATE.substitute(
        data_json=json.dumps(records),
        map_var=m.get_name(),
    )

    m.get_root().html.add_child(folium.Element(panel_html))
    m.get_root().script.add_child(folium.Element(script_js))
    return m


def main():
    records = build_records()
    print(f"Mappable records: {len(records)}")
    build_map(records).save(str(OUTPUT_PATH))
    print(f"Map written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
