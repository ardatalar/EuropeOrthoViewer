
from xml.etree import ElementTree as ET
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from typing import Dict, List, Optional

from qgis.core import QgsRasterLayer, QgsProject
from PyQt5.QtWidgets import QTreeWidgetItem, QMessageBox
from PyQt5.QtCore import Qt

from .net_utils import http_get_bytes  

NS = {
    "wmts": "http://www.opengis.net/wmts/1.0",
    "ows": "http://www.opengis.net/ows/1.1",
    "xlink": "http://www.w3.org/1999/xlink",
}


def _clean_url(url: str) -> str:
    return (url or "").strip()


def _build_caps_url(base_url: str) -> str:
    """
    Build a WMTS GetCapabilities URL from any base WMTS link (KVP or REST base).
    If the link is already a KVP URL, we override SERVICE/REQUEST conservatively.
    """
    parts = urlsplit(base_url.strip())
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q.update({
        "SERVICE": "WMTS",
        "REQUEST": "GetCapabilities",
    })
    parts = parts._replace(query=urlencode(q, doseq=True))
    return urlunsplit(parts)


def _normalize_service_base(url: str) -> str:
    """
    Return a clean base service URL to use in QGIS URI: keep existing params except
    those specific to GetCapabilities (SERVICE/REQUEST/VERSION).
    Retains the working scheme (http/https).
    """
    if not url:
        return ""
    parts = urlsplit(url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    for k in list(q.keys()):
        if k.lower() in {"service", "request", "version"}:
            q.pop(k, None)
    parts = parts._replace(query=urlencode(q, doseq=True))
    return urlunsplit(parts)


def _extract_gettile_base(xml_bytes: bytes) -> str:
    """
    From Capabilities, read OperationsMetadata/Operation name='GetTile'/DCP/HTTP/Get/@xlink:href.
    Return the href (possibly with query params). Empty string if not found.
    """
    root = ET.fromstring(xml_bytes)
    ops = root.find("ows:OperationsMetadata", NS)
    if ops is None:
        return ""
    for op in ops.findall("ows:Operation", NS):
        name = op.get("name") or ""
        if name.lower() != "gettile":
            continue
        dcp = op.find("ows:DCP", NS)
        if dcp is None:
            continue
        http = dcp.find("ows:HTTP", NS)
        if http is None:
            continue
        get = http.find("ows:Get", NS)
        if get is None:
            continue
        href = get.get(f"{{{NS['xlink']}}}href") or get.get("href") or ""
        return href.strip()
    return ""


def _parse_tile_matrix_sets(root: ET.Element) -> Dict[str, Dict]:
    """
    Return { tms_id: {"crs": <str>, "count": <int>} }
    """
    out: Dict[str, Dict] = {}
    contents = root.find("wmts:Contents", NS)
    if contents is None:
        return out

    for tms in contents.findall("wmts:TileMatrixSet", NS):
        id_el = tms.find("ows:Identifier", NS)
        crs_el = tms.find("ows:SupportedCRS", NS)
        if id_el is None:
            continue
        tms_id = (id_el.text or "").strip()
        crs = (crs_el.text or "").strip() if crs_el is not None else None
        count = len(tms.findall("wmts:TileMatrix", NS))
        out[tms_id] = {"crs": crs, "count": count}
    return out


def _prefer_format(fmts: List[str]) -> Optional[str]:
    """
    Choose a concrete image format. Filter out pseudo/union tokens like 'image/jpgpng'.
    Preference: PNG (png, png8, png32) -> any png-like -> JPEG -> first remaining.
    """
    if not fmts:
        return None

    lower_pairs = [(f, f.lower()) for f in fmts if f]
    filtered = [orig for (orig, low) in lower_pairs if low not in {"image/jpgpng"}]
    candidates = filtered if filtered else [orig for (orig, _) in lower_pairs]

    for pref in ("image/png", "image/png8", "image/png32"):
        for c in candidates:
            if c.lower() == pref:
                return c

    for c in candidates:
        if "png" in c.lower():
            return c

    for pref in ("image/jpeg", "image/jpg"):
        for c in candidates:
            if c.lower() == pref:
                return c

    return candidates[0] if candidates else None


def _prefer_matrix_set(sets: List[Dict]) -> Optional[str]:
    if not sets:
        return None

    def is_3857(crs: Optional[str]) -> bool:
        s = (crs or "").lower().replace("::", ":")
        return "3857" in s or "900913" in s or "webmercator" in s.replace(" ", "")

    def is_4326(crs: Optional[str]) -> bool:
        s = (crs or "").lower()
        return "4326" in s or "wgs84" in s.replace(" ", "")

    for s in sets:
        if is_3857(s.get("crs")):
            return s["id"]
    for s in sets:
        if is_4326(s.get("crs")):
            return s["id"]
    return sets[0]["id"]


def _to_qgis_authid(crs_str: Optional[str]) -> Optional[str]:
    if not crs_str:
        return None
    s = crs_str.strip()
    if s.upper().startswith("EPSG:"):
        return s.upper()
    if "epsg" in s.lower():
        parts = s.replace("::", ":").split(":")
        for token in reversed(parts):
            if token.isdigit():
                return f"EPSG:{token}"
    return None


def _parse_layers(root: ET.Element, tms_dict: Dict[str, Dict]) -> List[Dict]:
    """
    Return list of:
      {
        "identifier": str,
        "title": Optional[str],
        "formats": [str],
        "matrix_sets": [{"id": str, "crs": Optional[str]}],
        "styles": [str],
        "default_style": Optional[str],
        "default_format": Optional[str],
        "default_matrix_set": Optional[str]
      }
    """
    out: List[Dict] = []
    contents = root.find("wmts:Contents", NS)
    if contents is None:
        return out

    for layer in contents.findall("wmts:Layer", NS):
        ident_el = layer.find("ows:Identifier", NS)
        if ident_el is None:
            continue
        identifier = (ident_el.text or "").strip()
        if not identifier:
            continue

        title_el = layer.find("ows:Title", NS)
        title = (title_el.text or "").strip() if title_el is not None else identifier

        # Formats
        fmts = [(f.text or "").strip() for f in layer.findall("wmts:Format", NS)]
        fmts = [f for f in fmts if f]

        # Matrix sets
        ms_links = []
        for link in layer.findall("wmts:TileMatrixSetLink", NS):
            ms_el = link.find("wmts:TileMatrixSet", NS)
            if ms_el is None:
                continue
            ms_id = (ms_el.text or "").strip()
            if not ms_id:
                continue
            crs = tms_dict.get(ms_id, {}).get("crs")
            ms_links.append({"id": ms_id, "crs": crs})

        # Styles (detect isDefault="true" when present)
        styles: List[str] = []
        default_style: Optional[str] = None
        for st in layer.findall("wmts:Style", NS):
            sid_el = st.find("ows:Identifier", NS)
            sid = (sid_el.text or "").strip() if sid_el is not None else ""
            if not sid:
                continue
            styles.append(sid)
            is_def = (st.get("isDefault") or "").lower() in {"true", "1", "yes"}
            if is_def:
                default_style = sid
        if default_style is None:
            if any(s.lower() == "default" for s in styles):
                default_style = next(s for s in styles if s.lower() == "default")
            elif styles:
                default_style = styles[0]

        out.append({
            "identifier": identifier,
            "title": title,
            "formats": fmts,
            "matrix_sets": ms_links,
            "styles": styles,
            "default_style": default_style,
            "default_format": _prefer_format(fmts),
            "default_matrix_set": _prefer_matrix_set(ms_links),
        })
    return out



# ------------------------------- Public API ------------------------------- #

def load_wmts_layers(wmts_link: str, tree_widget) -> None:
    """
    Fetch WMTS capabilities and populate the tree with checkable items.
    Stores in each item:
      - Qt.UserRole: base WMTS URL (Capabilities-base; GetTile-base also saved in payload)
      - Qt.UserRole + 1: dict payload with formats/matrix_sets/styles/defaults + bases
    """
    wmts_link = _clean_url(wmts_link)
    errors = []

    try:
        caps_url = _build_caps_url(wmts_link)
        xml_bytes, used_caps_url = http_get_bytes(caps_url, timeout_ms=15000) 
        root = ET.fromstring(xml_bytes)

        tms_dict = _parse_tile_matrix_sets(root)
        layers = _parse_layers(root, tms_dict)
        if not layers:
            raise ValueError("No layers found in WMTS GetCapabilities.")

        caps_base = _normalize_service_base(used_caps_url)
        tile_base = _normalize_service_base(_extract_gettile_base(xml_bytes))

        tree_widget.clear()
        for lyr in layers:
            item = QTreeWidgetItem([lyr["identifier"], lyr["title"]])
            item.setCheckState(0, Qt.Unchecked)
            item.setData(0, Qt.UserRole, caps_base)
            payload = {
                "formats": lyr["formats"],
                "matrix_sets": lyr["matrix_sets"],
                "styles": lyr["styles"],
                "default_style": lyr["default_style"],
                "default_format": lyr["default_format"],
                "default_matrix_set": lyr["default_matrix_set"],
                "caps_base": caps_base,
                "tile_base": tile_base,
            }
            item.setData(0, Qt.UserRole + 1, payload)
            tree_widget.addTopLevelItem(item)
        return

    except (ET.ParseError, ValueError, RuntimeError) as e:
        errors.append(str(e))

    QMessageBox.critical(
        None,
        "WMTS Error",
        "Failed to read WMTS GetCapabilities from:\n"
        f"{wmts_link}\n\nDetails:\n" + "\n".join(errors)
    )


def add_wmts_layer(
    layer_identifier: str,
    wmts_link: str,
    matrix_set: Optional[str] = None,
    fmt: Optional[str] = None
) -> None:
    """
    Add a WMTS layer to the current QGIS project.
    Strategy: build a correct WMTS URI and try with the Capabilities base first,
    then with the advertised GetTile base if the first attempt fails.
    """
    wmts_link = _clean_url(wmts_link)

    try:
        caps_url = _build_caps_url(wmts_link)
        xml_bytes, used_caps_url = http_get_bytes(caps_url, timeout_ms=15000)  # QGIS NAM
        root = ET.fromstring(xml_bytes)

        tms_dict = _parse_tile_matrix_sets(root)
        layers = _parse_layers(root, tms_dict)

        # Locate layer by Identifier (exact/ci) or Title (ci)
        match = None
        low = layer_identifier.strip().lower()
        for L in layers:
            if L["identifier"] == layer_identifier:
                match = L
                break
        if match is None:
            for L in layers:
                if L["identifier"].lower() == low:
                    match = L
                    break
        if match is None:
            for L in layers:
                if (L.get("title") or "").strip().lower() == low:
                    match = L
                    break
        if match is None:
            raise ValueError(f"WMTS layer '{layer_identifier}' not found in capabilities.")

        chosen_ms = matrix_set or match["default_matrix_set"]
        if not chosen_ms:
            if match["matrix_sets"]:
                chosen_ms = match["matrix_sets"][0]["id"]
            else:
                raise ValueError(f"WMTS layer '{match['identifier']}' has no TileMatrixSet.")

        chosen_fmt = fmt or match["default_format"] or _prefer_format(match["formats"])
        if not chosen_fmt:
            raise ValueError(f"WMTS layer '{match['identifier']}' has no advertised image formats.")

        # CRS comes from the chosen matrix set (optional in URI)
        crs_authid = None
        for ms in match["matrix_sets"]:
            if ms["id"] == chosen_ms:
                crs_authid = _to_qgis_authid(ms.get("crs"))
                break

        # Choose a valid style identifier
        chosen_style = match.get("default_style") or (match.get("styles")[0] if match.get("styles") else "default")

        # Base URLs: try Capabilities-base first, then GetTile-base
        caps_base = _normalize_service_base(used_caps_url)
        tile_base = _normalize_service_base(_extract_gettile_base(xml_bytes))
        base_candidates = [b for b in [caps_base, tile_base] if b]

        # Build common param list
        common_params = [
            "contextualWMSLegend=0",
            f"layers={match['identifier']}",
            f"styles={chosen_style}",
            f"format={chosen_fmt}",
            f"tileMatrixSet={chosen_ms}",
        ]
        if crs_authid:
            common_params.insert(1, f"crs={crs_authid}")

        display_name = match.get("title") or match["identifier"]

        last_err = None
        for base_url in base_candidates:
            params = list(common_params)
            params.append(f"url={base_url}")
            uri = "&".join(params)
            layer = QgsRasterLayer(uri, display_name, "wms")  # WMTS via 'wms' provider
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                return
            else:
                last_err = f"Invalid with base: {base_url}"

        # If both failed
        raise RuntimeError(last_err or "Could not create WMTS layer with any base URL.")

    except (ET.ParseError, ValueError, RuntimeError) as e:
        QMessageBox.critical(
            None,
            "WMTS Error",
            f"Failed to add WMTS layer:\n{layer_identifier}\nfrom:\n{wmts_link}\n\n{e}"
        )
