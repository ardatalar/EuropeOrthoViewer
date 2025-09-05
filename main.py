
from PyQt5.QtWidgets import QAction, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt   
from qgis.core import QgsProject
from qgis.utils import iface

from .ui import EuropeOrthoDialog
from .wms_utils import load_wms_layers, add_wms_layer


try:
    from .wmts_utils import load_wmts_layers, add_wmts_layer
except Exception:  
    def load_wmts_layers(url, tree_widget):
        raise NotImplementedError("WMTS support not yet installed.")

    def add_wmts_layer(layer_identifier, wmts_link, matrix_set=None, fmt=None):
        raise NotImplementedError("WMTS support not yet installed.")

try:
    from .rest_utils import load_rest_layers, add_rest_layer
except Exception:  
    def load_rest_layers(url, tree_widget):
        raise NotImplementedError("ArcGIS REST support not yet installed.")

    def add_rest_layer(service_url, layer_identifier, fmt=None, where=None, time_params=None):
        raise NotImplementedError("ArcGIS REST support not yet installed.")

# Catalog
try:
    from .catalog import get_entry
except Exception:
    get_entry = None


def detect_service_type(url: str) -> str:
    """
    Heuristic detection from URL.
    Returns: 'WMS' | 'WMTS' | 'REST'
    """
    if not url:
        return "WMS"

    u = url.lower()

    if "/mapserver" in u or "/featureserver" in u or "/rest/services/" in u:
        return "REST"
    if "service=wmts" in u or "{tilematrix}" in u or "tilematrixset=" in u or "/wmts/" in u:
        return "WMTS"

    return "WMS"


class EuropeOrthoWMSPlugin:
    def __init__(self, iface_):
        self.iface = iface_
        self.dlg = None
        self.action = None

    def initGui(self):
        self.action = QAction(
            QIcon(":/resources/GIS.png"),
            "EuropeOrthoWMS",
            self.iface.mainWindow()
        )
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&EuropeOrthoWMS", self.action)

    def unload(self):
        if self.action:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu("&EuropeOrthoWMS", self.action)

    def run(self):
        if self.dlg is None:
            self.dlg = EuropeOrthoDialog(self.iface.mainWindow())
            self.dlg.set_project_crs(QgsProject.instance().crs().authid())  # fallback = EPSG:4326
            self.dlg.listBtn.clicked.connect(self._on_list_layers)
            self.dlg.addBtn.clicked.connect(self._on_add_selected)

        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()

    # --------- Internal helpers ---------

    def _current_service_type(self, url: str) -> str:
        """
        Resolve the service type:
        1. Explicit selector in UI (if present)
        2. Catalog entry (if dlg exposes a currentCatalogSelection and catalog.py exists)
        3. Fallback: URL auto-detect
        """
        # 1) explicit UI selector
        if hasattr(self.dlg, "serviceType") and callable(getattr(self.dlg, "serviceType")):
            st = (self.dlg.serviceType() or "").strip().upper()
            if st in {"WMS", "WMTS", "REST", "ARCGIS REST", "ARCGIS_REST"}:
                return "REST" if "REST" in st else st

        # 2) catalog type
        if get_entry and hasattr(self.dlg, "currentCatalogSelection"):
            try:
                country, region = self.dlg.currentCatalogSelection()  # should return (country, region)
                entry = get_entry(country, region)
                if entry and "type" in entry:
                    return entry["type"].upper()
            except Exception:
                pass

        # 3) fallback to heuristic
        return detect_service_type(url)

    # --------- Button slots ---------

    def _on_list_layers(self):
        url = self.dlg.urlEdit.text().strip()
        service_type = self._current_service_type(url)

        try:
            self.dlg.tree.clear()

            if service_type == "WMS":
                load_wms_layers(url, self.dlg.tree)
            elif service_type == "WMTS":
                load_wmts_layers(url, self.dlg.tree)
            elif service_type == "REST":
                load_rest_layers(url, self.dlg.tree)
            else:
                raise ValueError(f"Unknown service type: {service_type}")

        except NotImplementedError as e:
            QMessageBox.information(self.iface.mainWindow(), "Not available", str(e))
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), f"{service_type} Error", str(e))

    def _on_add_selected(self):
        url = self.dlg.urlEdit.text().strip()
        service_type = self._current_service_type(url)

        # Common UI fields 
        crs = self.dlg.crsLabel.text().strip() or "EPSG:4326"
        fmt = self.dlg.formatCombo.currentText().strip() or "image/jpeg"

        # Try to fetch selected items (preferred, to get stashed URLs/payloads)
        get_items = getattr(self.dlg, "selected_items", None)
        selected_items = get_items() if callable(get_items) else None

        if selected_items:
            entries = []
            for it in selected_items:
                name = it.text(0)  # layer identifier / name
                base_url = it.data(0, Qt.UserRole) or url
                payload = it.data(0, Qt.UserRole + 1)
                entries.append((name, base_url, payload))
        else:
            # Fallback to names only (uses the URL from the text field)
            names = self.dlg.selected_layer_names()
            if not names:
                QMessageBox.information(
                    self.iface.mainWindow(),
                    "No selection",
                    "Please tick at least one layer."
                )
                return
            # payload is unknown in this path; use None
            entries = [(n, url, None) for n in names]

        errors = []
        for name, effective_url, payload in entries:
            try:
                if service_type == "WMS":
                    add_wms_layer(name, effective_url, crs, fmt)

                elif service_type == "WMTS":
                    ms = None
                    wfmt = None
                    if isinstance(payload, dict):
                        ms = payload.get("default_matrix_set") or None
                        wfmt = payload.get("default_format") or None
                    add_wmts_layer(layer_identifier=name,
                                   wmts_link=effective_url,
                                   matrix_set=ms,
                                   fmt=wfmt or fmt)

                elif service_type == "REST":
                    add_rest_layer(service_url=effective_url,
                                   layer_identifier=name,
                                   fmt=fmt)

                else:
                    raise ValueError(f"Unknown service type: {service_type}")

            except Exception as e:
                errors.append(f"{name}: {e}")

        if errors:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Some layers failed",
                "\n".join(errors)
            )
