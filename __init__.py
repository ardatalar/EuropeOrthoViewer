try:
    from . import resources_rc  
except Exception:
    pass

def classFactory(iface):
    from .main import EuropeOrthoWMSPlugin
    return EuropeOrthoWMSPlugin(iface)
