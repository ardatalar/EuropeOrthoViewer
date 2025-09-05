
import json
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import requests
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidgetItem, QMessageBox
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer


# ------------------------------ Public API ------------------------------ #

def load_rest_layers(service_url: str, tree_widget) -> None:
    """
    Fetch ArcGIS REST (MapServer / FeatureServer / ImageServer) JSON and populate the tree.

    Each item added to 'tree_widget' has:
      - Column 0: layer name (string)
      - Column 1: "ID <id>"
      - Data(0, Qt.UserRole): cleaned base service URL (no query)
      - Data(0, Qt.UserRole + 1): payload dict with keys:
          {
            "service_type": "MAP" | "FEATURE",
            "id": <int>,
            "name": <str>,
            "geometryType": <str or None>,       # FeatureServer layers
            "formats": [<str>, ...]              # MapServer/ImageServer supported formats (normalized)
          }
    """
    base_url = _clean_base_url(service_url)
    try:
        info = _fetch_json(_ensure_json_suffix(base_url))
        svc_type = _detect_service_type_from_url(base_url)

        if svc_type == "UNKNOWN":
            svc_type = _detect_service_type_from_payload(info)

        if svc_type == "MAP":
            layers = info.get("layers") or []
            formats = _parse_supported_formats(info.get("supportedImageFormatTypes", ""))
            if not layers:
                raise ValueError("No layers advertised by MapServer/ImageServer.")

            for L in layers:
                lid = L.get("id")
                lname = L.get("name", f"Layer {lid}")
                item = QTreeWidgetItem([lname, f"ID {lid}"])
                item.setCheckState(0, Qt.Unchecked)
                item.setData(0, Qt.UserRole, base_url)
                payload = {
                    "service_type": "MAP",
                    "id": lid,
                    "name": lname,
                    "geometryType": None,
                    "formats": formats,
                }
                item.setData(0, Qt.UserRole + 1, payload)
                tree_widget.addTopLevelItem(item)

        elif svc_type == "FEATURE":
            layers = info.get("layers") or []
            if not layers:
                raise ValueError("No layers advertised by FeatureServer.")

            for L in layers:
                lid = L.get("id")
                lname = L.get("name", f"Layer {lid}")
                gtype = L.get("geometryType")
                item = QTreeWidgetItem([lname, f"ID {lid}"])
                item.setCheckState(0, Qt.Unchecked)
                item.setData(0, Qt.UserRole, base_url)
                payload = {
                    "service_type": "FEATURE",
                    "id": lid,
                    "name": lname,
                    "geometryType": gtype,
                    "formats": [],
                }
                item.setData(0, Qt.UserRole + 1, payload)
                tree_widget.addTopLevelItem(item)

        else:
            raise ValueError("Unsupported or unknown ArcGIS service URL. Use a MapServer or FeatureServer endpoint.")

    except (requests.RequestException, ValueError) as e:
        QMessageBox.critical(
            None,
            "ArcGIS REST Error",
            f"Failed to read ArcGIS REST service:\n{base_url}\n\n{e}"
        )


def add_rest_layer(
    service_url: str,
    layer_identifier: str,
    fmt: Optional[str] = None,
    where: Optional[str] = None,
    time_params: Optional[Tuple[int, int]] = None,
) -> None:
    """
    Add a MapServer/ImageServer (raster) or FeatureServer (vector) layer to the QGIS project.

    - 'service_url' can be the service root (e.g., .../MapServer) or a layer URL (.../MapServer/0)
      (we will normalize to the root for raster)
    - 'layer_identifier' can be a numeric id (as string/int) or layer name (case-insensitive)
    - 'fmt' (MapServer/ImageServer): preferred image format token (e.g., 'png32', 'png', 'jpg').
    - 'where' (FeatureServer): optional attribute filter via setSubsetString (client-side)
    """
    base_url = _clean_base_url(service_url)
    try:
        info = _fetch_json(_ensure_json_suffix(base_url))
        svc_type = _detect_service_type_from_url(base_url)
        if svc_type == "UNKNOWN":
            svc_type = _detect_service_type_from_payload(info)

        # Resolve target layer (id + name)
        target_id, target_name = _resolve_layer(info, layer_identifier)

        if svc_type == "FEATURE":
            lyr_url = f"{_strip_trailing_slash(base_url)}/{target_id}"
            display_name = target_name or f"Feature {target_id}"

            candidates = [
                f"url={lyr_url}",
                lyr_url,
            ]
            vlayer = None
            for src in candidates:
                vlayer = QgsVectorLayer(src, display_name, "arcgisfeatureserver")
                if vlayer.isValid():
                    break

            if vlayer is None or not vlayer.isValid():
                raise RuntimeError("Failed to create FeatureServer layer. URL may be inaccessible or provider missing.")

            if where:
                try:
                    vlayer.setSubsetString(where)
                except Exception:
                    pass

            QgsProject.instance().addMapLayer(vlayer)
            return

        elif svc_type == "MAP":
            # ---- MapServer/ImageServer raster layer ----
            # Always use the SERVICE ROOT for 'url=' and select sublayer via 'layers=show:<id>'
            svc_root = _strip_trailing_slash(base_url)  # .../MapServer

            # Available formats from service; choose a concrete one (lowercase tokens)
            formats = _parse_supported_formats(info.get("supportedImageFormatTypes", ""))
            chosen_fmt = _prefer_arcgis_format(fmt, formats)  

            display_name = target_name or f"Map {target_id}"
            rlayer = None

            candidate_param_lists = [
                [f"layers=show:{target_id}", f"format={chosen_fmt}", f"url={svc_root}"],
                [f"layers=show:{target_id}",                         f"url={svc_root}"],
                [                                                     f"url={svc_root}"],
            ]

            for plist in candidate_param_lists:
                uri = "&".join(plist)
                rlayer = QgsRasterLayer(uri, display_name, "arcgismapserver")
                if rlayer.isValid():
                    try:
                        if chosen_fmt:
                            rlayer.setCustomProperty("imageFormat", chosen_fmt)
                        rlayer.setCustomProperty("layers", f"show:{target_id}")
                    except Exception:
                        pass
                    break

            if rlayer is None or not rlayer.isValid():
                raise RuntimeError(
                    "Failed to create MapServer layer in QGIS. "
                    "The server may be private or the provider is unavailable."
                )

            QgsProject.instance().addMapLayer(rlayer)
            return

        else:
            raise ValueError("Unsupported or unknown ArcGIS service.")

    except (requests.RequestException, ValueError, RuntimeError) as e:
        QMessageBox.critical(
            None,
            "ArcGIS REST Error",
            f"Failed to add ArcGIS REST layer from:\n{base_url}\n\n{e}"
        )


# ------------------------------ Helpers ------------------------------ #

def _fetch_json(url: str, timeout: int = 15) -> Dict:
    """GET JSON from ArcGIS REST; ensures '?f=json' is present."""
    resp = requests.get(_ensure_json_suffix(url), timeout=timeout, headers={"User-Agent": "QGIS-Plugin-REST/1.0"})
    resp.raise_for_status()
    return resp.json()


def _ensure_json_suffix(url: str) -> str:
    """Ensure '?f=json' (or '&f=json') is present."""
    if "f=json" in url.lower():
        return url
    sep = "&" if ("?" in url) else "?"
    return f"{url}{sep}f=json"


def _clean_base_url(url: str) -> str:
    """Drop query string and fragment; keep scheme/host/path."""
    parts = urlsplit(url.strip())
    parts = parts._replace(query="", fragment="")
    return urlunsplit(parts)


def _strip_trailing_slash(u: str) -> str:
    return u[:-1] if u.endswith("/") else u


def _detect_service_type_from_url(url: str) -> str:
    u = url.lower()
    if "/featureserver" in u:
        return "FEATURE"
    if "/mapserver" in u:
        return "MAP"
    if "/imageserver" in u:
        return "MAP"
    return "UNKNOWN"


def _detect_service_type_from_payload(info: Dict) -> str:
    layers = info.get("layers") or []
    if layers:
        if any("geometryType" in L for L in layers):
            return "FEATURE"
        return "MAP"
    return "UNKNOWN"


def _resolve_layer(service_info: Dict, layer_identifier: str) -> Tuple[int, Optional[str]]:
    layers = service_info.get("layers") or []
    if not layers:
        raise ValueError("Service does not advertise any 'layers'.")

    # numeric id?
    if isinstance(layer_identifier, int) or (isinstance(layer_identifier, str) and layer_identifier.isdigit()):
        lid = int(layer_identifier)
        for L in layers:
            if int(L.get("id")) == lid:
                return lid, L.get("name")
        raise ValueError(f"Layer id '{layer_identifier}' not found.")

    # by name (ci)
    needle = (layer_identifier or "").strip().lower()
    for L in layers:
        if (L.get("name") or "").strip().lower() == needle:
            return int(L.get("id")), L.get("name")
    for L in layers:
        if needle and needle in (L.get("name") or "").strip().lower():
            return int(L.get("id")), L.get("name")

    raise ValueError(f"Layer '{layer_identifier}' not found by name.")


def _parse_supported_formats(fmt_str: str) -> List[str]:
    """
    Normalize ArcGIS 'supportedImageFormatTypes' into a list (lower-case tokens).
    Example input: 'PNG32, PNG24, PNG8, JPG, BIL, BMP, GIF, TIFF'
    """
    tokens = [t.strip().lower() for t in (fmt_str or "").split(",") if t.strip()]
    return tokens


def _prefer_arcgis_format(requested_fmt: Optional[str], available: List[str]) -> str:
    """
    Choose a good image format for MapServer export.
    Priority: requested -> png32 -> png24 -> png8 -> png -> jpg/jpeg -> first/PNG32.
    """
    if requested_fmt:
        r = requested_fmt.strip().lower()
        if r in available:
            return r

    prefs = ["png32", "png24", "png8", "png", "jpg", "jpeg"]
    for p in prefs:
        if p in available:
            return p

    return available[0] if available else "png32"
