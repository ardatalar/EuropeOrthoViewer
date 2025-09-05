
from xml.etree import ElementTree as ET
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from qgis.core import QgsRasterLayer, QgsProject
from PyQt5.QtWidgets import QTreeWidgetItem, QMessageBox
from PyQt5.QtCore import Qt

from .net_utils import http_get_bytes  

NS_WMS = "{http://www.opengis.net/wms}"
NS_XLINK = "{http://www.w3.org/1999/xlink}"


def clean_url(url: str) -> str:
    """Strip whitespace from URL."""
    return (url or "").strip()


def _build_caps_url(base_url: str, version: str) -> str:
    """Build a GetCapabilities URL from any base WMS link."""
    parts = urlsplit(base_url.strip())
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q.update({
        "SERVICE": "WMS",
        "REQUEST": "GetCapabilities",
        "VERSION": version,
    })
    parts = parts._replace(query=urlencode(q, doseq=True))
    return urlunsplit(parts)


def _normalize_service_base(url: str) -> str:
    """
    Keep scheme/host/path and non-capability params; drop GetCapabilities-specific keys.
    This preserves the same working scheme (http/https) for subsequent GetMap calls.
    """
    parts = urlsplit(url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    for k in list(q.keys()):
        if k.lower() in {"service", "request", "version"}:
            q.pop(k, None)
    parts = parts._replace(query=urlencode(q, doseq=True))
    return urlunsplit(parts)


# -------------------- Namespace-agnostic XML helpers -------------------- #

def _findall_any(elem: ET.Element, localname: str):
    """
    Namespace-agnostic findall for a given local tag name.
    Works for WMS 1.3.0 (namespaced) and 1.1.1 (often no namespace).
    """
    return elem.findall(f"{'{*}'}{localname}") + elem.findall(localname)


def _first_any(elem: ET.Element, localname: str):
    """Namespace-agnostic find for the first occurrence of a tag."""
    res = elem.find(f"{'{*}'}{localname}")
    return res if res is not None else elem.find(localname)


# -------------------- Capabilities parsing (layers/CRS) -------------------- #

def _parse_layers_from_caps(xml_bytes: bytes):
    """
    Parses WMS GetCapabilities XML recursively and accumulates inherited CRS/SRS.
    Returns a list of dicts: {name: ..., title: ..., crs_list: [...]}
    - Supports WMS 1.3.0 (CRS) and 1.1.1 (SRS), with or without namespaces.
    """
    def normalize_crs_tokens(text: str):
        """
        SRS/CRS elements in 1.1.1 can contain multiple codes separated by spaces/commas.
        Yield individual tokens.
        """
        if not text:
            return []
        tokens = []
        for chunk in text.replace(",", " ").split():
            if chunk:
                tokens.append(chunk.strip())
        return tokens

    def walk_layers(elem: ET.Element, inherited_crs: list):
        layers = []

        # Collect this element's CRS/SRS entries (support both tags)
        own_crs = []
        for e in _findall_any(elem, "CRS"):
            own_crs.extend(normalize_crs_tokens(e.text or ""))
        for e in _findall_any(elem, "SRS"):
            own_crs.extend(normalize_crs_tokens(e.text or ""))

        combined_crs = inherited_crs + own_crs

        name_el = _first_any(elem, "Name")
        title_el = _first_any(elem, "Title")

        # If this is a named (leaf) layer, store it
        if name_el is not None and (name_el.text or "").strip():
            normalized_crs = []
            for crs in combined_crs:
                if not crs:
                    continue
                cs = crs.strip()
                up = cs.upper()
                if up.startswith("EPSG:"):
                    normalized_crs.append(up)
                elif "EPSG" in up:
                    # handle URN/OGC forms like "urn:ogc:def:crs:EPSG::3857"
                    parts = cs.replace("::", ":").split(":")
                    for token in reversed(parts):
                        if token.isdigit():
                            normalized_crs.append(f"EPSG:{token}")
                            break

            layers.append({
                "name": name_el.text.strip(),
                "title": (title_el.text.strip() if (title_el is not None and title_el.text) else name_el.text.strip()),
                "crs_list": sorted(set(normalized_crs))
            })

        for child in _findall_any(elem, "Layer"):
            if child is elem:
                continue
            layers += walk_layers(child, combined_crs)

        return layers

    root = ET.fromstring(xml_bytes)

    # Try capability root, then fallback to first Layer anywhere
    root_layer = None
    cap = _first_any(root, "Capability")
    if cap is not None:
        root_layer = _first_any(cap, "Layer")
    if root_layer is None:
        root_layer = _first_any(root, "Layer")
    if root_layer is None:
        return []

    all_layers = walk_layers(root_layer, [])

    seen, uniq = set(), []
    for d in all_layers:
        if d["name"] not in seen:
            uniq.append(d)
            seen.add(d["name"])

    return uniq


# -------------------- Capabilities parsing (GetMap URL) -------------------- #

def _extract_getmap_base(xml_bytes: bytes) -> str:
    """
    Parse Capabilities for the Request->GetMap->DCPType/HTTP->Get->OnlineResource@xlink:href.
    Return the href (including any query params). Fallback to empty string if not found.
    Namespace-agnostic and tolerant to 'DCP' vs 'DCPType'.
    """
    root = ET.fromstring(xml_bytes)

    cap = _first_any(root, "Capability")
    if cap is None:
        cap = root

    req = _first_any(cap, "Request")
    if req is None:
        return ""

    getmap = _first_any(req, "GetMap")
    if getmap is None:
        return ""

    dcp = _first_any(getmap, "DCPType")
    if dcp is None:
        dcp = _first_any(getmap, "DCP")
    if dcp is None:
        return ""

    http = _first_any(dcp, "HTTP")
    if http is None:
        return ""

    get = _first_any(http, "Get")
    if get is None:
        return ""

    or_el = _first_any(get, "OnlineResource")
    if or_el is None:
        return ""

    href = or_el.get(NS_XLINK + "href") or or_el.get("href") or ""
    return href.strip()



# ------------------------------ Public API ------------------------------ #

def load_wms_layers(wms_link, tree_widget):
    """
    Fetch WMS capabilities and populate the tree widget with available layers.

    Stores in each item:
    - Qt.UserRole: base WMS URL (advertised GetMap href when available; else working caps URL)
    - Qt.UserRole + 1: layer-supported CRS list
    """
    wms_link = clean_url(wms_link)
    errors = []

    for ver in ("1.3.0", "1.1.1"):
        try:
            caps_url = _build_caps_url(wms_link, ver)
            xml_bytes, used_caps_url = http_get_bytes(caps_url, timeout_ms=15000) 

            # 1) Parse layers (namespace-agnostic; CRS+SRS)
            layers = _parse_layers_from_caps(xml_bytes)
            if not layers:
                errors.append(f"No layers found in capabilities (version {ver}).")
                continue

            # 2) Prefer the server-advertised GetMap endpoint 
            advertised_getmap = _extract_getmap_base(xml_bytes)
            base_url = _normalize_service_base(advertised_getmap or used_caps_url)

            tree_widget.clear()
            for lyr in layers:
                item = QTreeWidgetItem([lyr["name"], lyr["title"]])
                item.setCheckState(0, Qt.Unchecked)
                item.setData(0, Qt.UserRole, base_url)
                item.setData(0, Qt.UserRole + 1, lyr.get("crs_list", []))
                tree_widget.addTopLevelItem(item)

            return  

        except (ET.ParseError, RuntimeError) as e:
            errors.append(f"{ver}: {e}")

    QMessageBox.critical(
        None,
        "WMS Error",
        "Failed to read WMS GetCapabilities from:\n"
        f"{wms_link}\n\nDetails:\n" + "\n".join(errors)
    )


def add_wms_layer(layer_name, wms_link, crs=None, img_format="image/jpeg"):
    """
    Add a WMS layer to the QGIS project using the chosen CRS and image format.

    Defaults:
    - CRS: current project CRS (if not specified)
    - Format: image/jpeg (better for orthophotos)
    """
    wms_link = clean_url(wms_link)
    if not crs:
        crs = QgsProject.instance().crs().authid() or "EPSG:4326"

    params = [
        "contextualWMSLegend=0",
        f"crs={crs}",
        "dpiMode=7",
        f"format={img_format}",
        f"layers={layer_name}",
        "styles=",
        f"url={wms_link}",  
    ]
    uri = "&".join(params)

    layer = QgsRasterLayer(uri, layer_name, "wms")
    if layer.isValid():
        QgsProject.instance().addMapLayer(layer)
    else:
        QMessageBox.critical(
            None,
            "Error",
            f"Failed to add WMS layer:\n{layer_name}\nfrom:\n{wms_link}\n\n"
            f"CRS: {crs}\nFormat: {img_format}"
        )
