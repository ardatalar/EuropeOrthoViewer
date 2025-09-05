
from typing import Dict, Optional, Tuple, List, Literal

ServiceType = Literal["WMS", "WMTS", "REST"]


# CATALOG[country][region] -> {"type": <ServiceType>, "url": <str>}
CATALOG: Dict[str, Dict[str, Dict[str, str]]] = {
    "Belgium": {
        "All": {"type": "WMS", "url": "https://wms.ngi.be/inspire/ortho/service"},
    },
    "Austria": {
        "All": {"type": "WMS", "url": "https://wsa.bev.gv.at/GeoServer/Interceptor/Wms/OI/INSPIRE_KUNDEN-382e30c7-69df-4a53-9331-c44821d9916e?REQUEST=GetCapabilities&SERVICE=WMS&VERSION=1.3.0"},
    },
    "Croatia": {
        "All": {"type": "WMS", "url": "https://geoportal.dgu.hr/services/inspire/orthophoto_lidar_2022_2023/wms"},
    },
    "Czech Republic": {
        "All": {"type": "WMS", "url": "https://geoportal.cuzk.cz/WMS_INSPIRE_ORTOFOTO/WMService.aspx"},
    },
    "Estonia": {
        "All": {"type": "WMS", "url": "https://inspire.geoportaal.ee/geoserver/OI_ortofoto/ows?SERVICE=WMS&REQUEST=GetCapabilities"},
    },
    "France": {
        "All": {"type": "WMS", "url": "https://data.geopf.fr/wms-r/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"},
    },
    "Greece": {
        "All": {"type": "WMS", "url": "http://gis.ktimanet.gr/wms/wmsopen/wmsserver.aspx?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0"},
    },
    "Hungary": {
        "All": {"type": "WMS", "url": "https://inspire.lechnerkozpont.hu/geoserver/OI.2023/wms?request=getCapabilities"},
    },
    "Latvia": {
        "All": {"type": "WMS", "url": "https://lvmgeoserver.lvm.lv/geoserver/ows?service=wms&version=1.3.0&request=GetCapabilities&layer=public:Orto_LKS"},
    },
    "Luxembourg": {
        "All": {"type": "WMS", "url": "https://wms.inspire.geoportail.lu/geoserver/oi/wms?service=WMS&version=1.3.0&request=GetCapabilities"},
    },
    "Malta": {
        "All": {"type": "WMS", "url": "https://malta.coverage.wetransform.eu/capabilities/ortho-wms-caps.xml"},
    },
    "Moldova": {
        "All": {"type": "WMS", "url": "https://geodata.gov.md/geoserver/orthophoto/wms?"},
    },
    "Netherlands": {
        "All": {"type": "WMS", "url": "https://service.pdok.nl/hwh/luchtfotorgb/wms/v1_0?request=GetCapabilities&service=wms;layerMask=/;version=1.3.0"},
    },
    "Poland": {
        "All": {"type": "WMS", "url": "https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMS/StandardResolution"},
    },
    "Portugal": {
        "All": {"type": "WMS", "url": "https://ortos.dgterritorio.gov.pt/wms/ortosat2023?service=WMS&request=GetCapabilities"},
    },
    "Slovakia": {
        "All": {"type": "WMS", "url": "https://zbgisws.skgeodesy.sk/zbgis_ortofoto_wms/service.svc/get?service=WMS&version=1.3.0&request=GetCapabilities"},
    },
    "Slovenia": {
        "All": {"type": "WMS", "url": "https://ipi.eprostor.gov.si/wms-si-gurs-dts/wms?request=getCapabilities"},
    },
    "Spain": {
        "All": {"type": "WMS", "url": "https://www.ign.es/wms-inspire/pnoa-ma?request=GetCapabilities&service=WMS&version=1.3.0"},
    },
    "Bulgaria": {
        "All": {"type": "WMS", "url": "http://inspire.mzh.government.bg:8080/geoserver/ows?service=wms&version=1.3.0&request=GetCapabilities"},
    },
    "Europe": {
        "All": {"type": "WMS", "url": "https://sgx.geodatenzentrum.de/wms_sen2europe"},
    },
    "Denmark": {
        "All": {"type": "WMS", "url": "https://api.dataforsyningen.dk/oi_inspire?SERVICE=WMS&REQUEST=GetCapabilities"},
    },
    "Cyprus": {
        "All": {"type": "REST", "url": "https://eservices.dls.moi.gov.cy/arcgis/rest/services/BASEMAPS/Imagery_Orthophoto_2014_10cm/MapServer"},
    },
    "Liechtenstein": {
        "All": {"type": "WMS", "url": "https://service.geo.llv.li/wmsli/service"},
    },
    "Lithuania": {
        "All": {"type": "WMS", "url": "https://www.geoportal.lt/qgisserver/oi?VERSION=1.3.0"},
    },
    "Norway": {
        "All": {"type": "WMTS", "url": "http://opencache.statkart.no/gatekeeper/gk/gk.open_nib_utm32_wmts_v2?SERVICE=WMTS&REQUEST=GetCapabilities"},
    },
    "Romania": {
        "All": {"type": "REST", "url": "https://inspire.geomil.ro/network/rest/services/INSPIRE/OI_View/MapServer"},
    },

    # Germany (states)
    "Germany": {
        "Bavaria": {"type": "WMS", "url": "https://geoservices.bayern.de/od/wms/dop/v1/dop20"},
        "Hesse": {"type": "WMS", "url": "https://www.geoportal.hessen.de/mapbender/php/mod_showMetadata.php/../wms.php?layer_id=52119&PHPSESSID=lgdh3l3v538npt7n8sutqqouq5&INSPIRE=1&VERSION=1.1.1"},
        "North Rhine-Westphalia": {"type": "WMS", "url": "https://www.wms.nrw.de/geobasis/wms_nw_dop?VERSION=1.3.0"},
        "Baden-Württemberg": {"type": "WMS", "url": "https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_LGL-BW_ATKIS_DOP_20_C"},
        "Berlin & Brandenburg": {"type": "WMS", "url": "https://isk.geobasis-bb.de/mapproxy/dop20c/service/wms"},
        "Bremen": {"type": "WMS", "url": "https://geodienste.bremen.de/wms_dop10_2023?VERSION=1.3.0"},
        "Hamburg": {"type": "WMS", "url": "https://geodienste.hamburg.de/wms_dop_zeitreihe_unbelaubt?Version=1.3.0"},
        "Lower Saxony": {"type": "WMS", "url": "https://opendata.lgln.niedersachsen.de/doorman/noauth/dop_wms"},
        "Mecklenburg-Vorpommern": {"type": "WMS", "url": "https://www.geodaten-mv.de/dienste/adv_dop"},
        "Rhineland-Palatinate": {"type": "WMS", "url": "https://www.geoportal.rlp.de/mapbender/php/wms.php?layer_id=61675&VERSION=1.1.1&withChilds=1"},
        "Saarland": {"type": "WMS", "url": "https://geoportal.saarland.de/mapbender/php/wms.php?inspire=1&layer_id=46747&withChilds=1"},
        "Saxony": {"type": "WMS", "url": "https://geodienste.sachsen.de/wms_geosn_dop-rgb/guest"},
        "Saxony-Anhalt": {"type": "WMS", "url": "https://www.geodatenportal.sachsen-anhalt.de/wss/service/ST_LVermGeo_DOP_WMS_OpenData/guest"},
        "Schleswig-Holstein": {"type": "WMS", "url": "https://dienste.gdi-sh.de/WMS_SH_DOP20col_OpenGBD?version=1.3.0"},
        "Thuringia": {"type": "WMS", "url": "https://www.geoproxy.geoportal-th.de/geoproxy/services/DOP"},
    },

    # Italy (national + regions)
    "Italy": {
        "All": {"type": "WMS", "url": "http://wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/raster/ortofoto_colore_12.map&version=1.3.0"},

        "Abruzzo": {"type": "WMS", "url": "http://geocatalogo.regione.abruzzo.it/erdas-iws/ogc/wms/"},
        "Aosta Valley": {"type": "WMS", "url": "https://geoservizi.regione.vda.it/geoserver/sctBaseMap/wms"},
        "Apulia": {"type": "WMS", "url": "http://webapps.sit.puglia.it/arcgis/services/BaseMaps/Ortofoto2019/ImageServer/WMSServer"},
        "Basilicata": {"type": "WMS", "url": "http://rsdi.regione.basilicata.it/geoserver/wms"},
        "Campania": {"type": "WMS", "url": "https://sit2.regione.campania.it/geoserver/RegioneCampania.Catalogo/wms?layers=sitdbo_reticolo_idrografico"},
        "Emilia-Romagna": {"type": "WMS", "url": "https://servizigis.regione.emilia-romagna.it/wms/agea2023_rgb"},
        "Friuli-Venezia Giulia": {"type": "WMS", "url": "https://irdat-ortofoto.regione.fvg.it/geoserver/ortofoto/ows"},
        "Lazio": {"type": "WMS", "url": "http://wms.pcn.minambiente.it/ogc?MAP=/ms_ogc/WMS_v1.3/raster/ortofoto_colore_08.map&LAYERS=OI.ORTOIMMAGINI.2008.33&STYLES=default&CRS=%7Bproj%7D&WIDTH=%7Bwidth%7D&HEIGHT=%7Bheight%7D&BBOX=%7Bbbox%7D&VERSION=1.3.0"},
        "Liguria": {"type": "WMS", "url": "https://geoservizi.regione.liguria.it/geoserver/M2555/wms?version=1.3.0&request=getcapabilities"},
        "Lombardy": {"type": "WMS", "url": "https://www.cartografia.servizirl.it/arcgis2/services/BaseMap/Ortofoto2021/ImageServer/WMSServer?_jsfBridgeRedirect=true"},
        "Marche": {"type": "WMS", "url": "http://wms.cartografia.marche.it/geoserver/AGEA2019/wms"},
        "Piedmont": {"type": "WMTS", "url": "https://opengis.csi.it/mp/regp_agea_2021?REQUEST=GetCapabilities&SERVICE=WMTS"},
        "Sardinia": {"type": "WMS", "url": "https://webgis.regione.sardegna.it/geoserverraster/ows"},
        "Sicily": {"type": "WMS", "url": "https://map.sitr.regione.sicilia.it/gis/services/ortofoto/ortofoto_2013_25cm_sicilia/MapServer/WMSServer?version=1.3.0"},
        "South Tyrol": {"type": "WMS", "url": "http://geoservices.buergernetz.bz.it/mapproxy/ows?version=1.3.0"},
        "Trentino": {"type": "WMS", "url": "https://siat.provincia.tn.it/geoserver/stem/ecw-rgb-2015/wms"},
        "Tuscany": {"type": "WMS", "url": "https://www502.regione.toscana.it/ows_ofc/com.rt.wms.RTmap/wms?map=owsofc_rt"},
        "Umbria": {"type": "WMS", "url": "https://siat.regione.umbria.it/arcgis/services/public/ORTOFOTO_2020_ETRF2000_UTM33N/MapServer/WMSServer"},
        "Veneto": {"type": "WMTS", "url": "https://idt2.regione.veneto.it/gwc/service/wmts"},
    },
}


# ---------- Helper API ---------- #

def get_entry(country: str, region: str = "All") -> Optional[Dict[str, str]]:
    """
    Return {"type": <ServiceType>, "url": <str>} for the given country/region,
    or None if not found.
    """
    return CATALOG.get(country, {}).get(region)


def list_countries() -> List[str]:
    """Sorted list of available countries."""
    return sorted(CATALOG.keys())


def list_regions(country: str) -> List[str]:
    """Sorted list of regions for a country."""
    return sorted(CATALOG.get(country, {}).keys())


# If older code expects a flat mapping (country -> region -> url), expose it read-only.
COUNTRY_WMS: Dict[str, Dict[str, str]] = {
    country: {region: entry["url"] for region, entry in regions.items()}
    for country, regions in CATALOG.items()
}
