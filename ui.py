
from PyQt5 import QtCore, QtGui, QtWidgets


try:
    from .catalog import CATALOG as _CATALOG
    _HAS_STRUCTURED = True
except Exception:
    from .catalog import COUNTRY_WMS as _LEGACY_COUNTRY_WMS

    _CATALOG = {
        country: {
            region: {"type": "WMS", "url": url}
            for region, url in (regions.items() if isinstance(regions, dict) else {"All": regions}.items())
        }
        for country, regions in _LEGACY_COUNTRY_WMS.items()
    }
    _HAS_STRUCTURED = False


class EuropeOrthoDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EuropeOrthoViewer")
        self.setWindowIcon(QtGui.QIcon(":/resources/GIS.png"))
        self.resize(800, 540)

        v = QtWidgets.QVBoxLayout(self)

        # --- Top row: Country + Region + URL + List Layers ---
        row = QtWidgets.QHBoxLayout()

        self.countryCombo = QtWidgets.QComboBox()
        self.countryCombo.addItems(sorted(_CATALOG.keys()))
        self.countryCombo.currentIndexChanged.connect(self._on_country_changed)

        self.regionCombo = QtWidgets.QComboBox()
        self.regionCombo.setMinimumWidth(100)
        self.regionCombo.currentIndexChanged.connect(self._on_region_changed)

        self.urlEdit = QtWidgets.QLineEdit()
        self.listBtn = QtWidgets.QPushButton("List Layers")

        row.addWidget(QtWidgets.QLabel("Country:"))
        row.addWidget(self.countryCombo)
        row.addSpacing(8)
        row.addWidget(QtWidgets.QLabel("Region:"))
        row.addWidget(self.regionCombo)
        row.addSpacing(8)
        row.addWidget(QtWidgets.QLabel("Service URL:"))
        row.addWidget(self.urlEdit, 1)
        row.addWidget(self.listBtn)
        v.addLayout(row)

        # --- Options row: CRS + format ---
        opt = QtWidgets.QHBoxLayout()

        self.crsLabel = QtWidgets.QLabel("EPSG:4326")  
        self.crsSelectBtn = QtWidgets.QPushButton("Select CRS")
        self.crsSelectBtn.setToolTip("Choose from CRS options advertised by the service")
        self.crsSelectBtn.clicked.connect(self._on_select_crs)

        self.formatCombo = QtWidgets.QComboBox()
        self.formatCombo.addItems(["image/jpeg", "image/png"])

        opt.addWidget(QtWidgets.QLabel("CRS:"))
        opt.addWidget(self.crsLabel)
        opt.addWidget(self.crsSelectBtn)
        opt.addSpacing(10)
        opt.addWidget(QtWidgets.QLabel("Format:"))
        opt.addWidget(self.formatCombo)
        opt.addStretch(1)
        v.addLayout(opt)

        # --- Layers tree ---
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["Layer Name / Identifier", "Title"])
        v.addWidget(self.tree, 1)

        # --- Bottom buttons ---
        btns = QtWidgets.QHBoxLayout()
        self.addBtn = QtWidgets.QPushButton("Add Selected")
        self.closeBtn = QtWidgets.QPushButton("Close")
        btns.addStretch(1)
        btns.addWidget(self.addBtn)
        btns.addWidget(self.closeBtn)
        v.addLayout(btns)

        self.closeBtn.clicked.connect(self.close)

        # Initialize dropdowns
        self._on_country_changed()

    # ----------------- Catalog / URL binding -----------------

    def _on_country_changed(self):
        """Update region list based on selected country."""
        country = self.countryCombo.currentText()
        regions = _CATALOG.get(country, {})

        self.regionCombo.clear()
        self.regionCombo.addItems(sorted(regions.keys()) or ["All"])
        self._on_region_changed()

    def _on_region_changed(self):
        """Update URL based on selected region."""
        country = self.countryCombo.currentText()
        region = self.regionCombo.currentText()

        entry = _CATALOG.get(country, {}).get(region)
        url = ""
        if isinstance(entry, dict):
            url = entry.get("url", "")
        elif isinstance(entry, str):
            url = entry

        self.urlEdit.setText(url)

    def currentCatalogSelection(self):
        return self.countryCombo.currentText(), self.regionCombo.currentText()

    # ----------------- CRS handling -----------------

    def _on_select_crs(self):
        supported_crs = self.get_all_supported_crs()
        if not supported_crs:
            QtWidgets.QMessageBox.warning(
                self, "No CRS Info",
                "No CRS options available. Please click 'List Layers' first."
            )
            return

        crs, ok = QtWidgets.QInputDialog.getItem(
            self,
            "Select CRS",
            "Supported Coordinate Reference Systems:",
            supported_crs,
            current=0,
            editable=False
        )

        if ok and crs:
            self.crsLabel.setText(crs)

    def _normalize_epsg(self, s: str) -> str:
        """Best-effort: convert OGC URN to EPSG:XXXX."""
        if not s:
            return ""
        t = s.strip()
        if t.upper().startswith("EPSG:"):
            return t.upper()
        if "epsg" in t.lower():
            parts = t.replace("::", ":").split(":")
            for token in reversed(parts):
                if token.isdigit():
                    return f"EPSG:{token}"
        return ""

    def get_all_supported_crs(self):
        """
        Collect CRS codes from currently listed layers.

        WMS layout (your wms_utils):
          - Qt.UserRole + 1 holds a list of CRS strings (e.g., ["EPSG:3857", "EPSG:4326", ...])

        WMTS layout (our wmts_utils):
          - Qt.UserRole + 1 holds a dict payload containing "matrix_sets": [{"id": "...", "crs": "..."}]
        """
        crs_set = set()
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            payload = it.data(0, QtCore.Qt.UserRole + 1)

            # WMS case: list of CRS strings
            if isinstance(payload, list):
                for crs in payload:
                    if isinstance(crs, str):
                        norm = self._normalize_epsg(crs) or (crs if crs.startswith("EPSG:") else "")
                        if norm:
                            crs_set.add(norm)

            # WMTS case: dict payload -> look into matrix_sets
            elif isinstance(payload, dict):
                msets = payload.get("matrix_sets") or []
                for ms in msets:
                    crs = self._normalize_epsg(ms.get("crs", ""))
                    if crs:
                        crs_set.add(crs)

           

        return sorted(crs_set)

    def set_project_crs(self, authid: str = "EPSG:4326"):
        """Prefill CRS label with project CRS or fallback."""
        self.crsLabel.setText(authid)

    # ----------------- Tree population helpers (WMS-style) -----------------

    def populate_layers(self, layers):
        """layers: list of dicts with keys name, title, crs_list."""
        self.tree.clear()
        for lyr in layers:
            item = QtWidgets.QTreeWidgetItem([lyr["name"], lyr.get("title", lyr["name"])])
            item.setCheckState(0, QtCore.Qt.Unchecked)
            item.setData(0, QtCore.Qt.UserRole + 1, lyr.get("crs_list", []))
            self.tree.addTopLevelItem(item)

    # ----------------- Selection helpers -----------------

    def selected_layer_names(self):
        """Legacy: return only names of checked items (works for WMS & WMTS)."""
        names = []
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            if it.checkState(0) == QtCore.Qt.Checked:
                names.append(it.text(0))
        return names

    def selected_items(self):
        """
        Preferred by main.py when available: return the actual checked items,
        so add handlers can read per-item data (like cleaned base URL).
        """
        items = []
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            if it.checkState(0) == QtCore.Qt.Checked:
                items.append(it)
        return items
