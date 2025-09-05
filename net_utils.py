from typing import Tuple, Optional
from PyQt5.QtCore import QEventLoop, QTimer, QUrl
from PyQt5.QtNetwork import QNetworkRequest, QNetworkReply
from qgis.PyQt.QtNetwork import QNetworkRequest as QgsQNetworkRequest  # safety across builds
from qgis.core import QgsNetworkAccessManager

_DEFAULT_TIMEOUT_MS = 15000
_MAX_REDIRECTS = 5
_UA = b"QGIS-Plugin-EuropeOrtho/1.0"

def _make_request(url: str) -> QNetworkRequest:
    req = QNetworkRequest(QUrl(url))
    req.setRawHeader(b"User-Agent", _UA)
    req.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
    return req

def _blocking_get(url: str, timeout_ms: int) -> Tuple[Optional[bytes], Optional[str]]:
    """Returns (bytes, final_url) or (None, error_text)."""
    nam = QgsNetworkAccessManager.instance()
    req = _make_request(url)
    reply = nam.get(req)

    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    reply.finished.connect(loop.quit)
    timer.start(timeout_ms)
    loop.exec_()

    if timer.isActive():  # finished not timed out
        timer.stop()
    else:  # timeout
        reply.abort()
        reply.deleteLater()
        return None, f"Timeout after {timeout_ms} ms"

    err = reply.error()
    redirects = 0
    while err == QNetworkReply.NoError:
        redir = reply.attribute(QNetworkRequest.RedirectionTargetAttribute)
        if redir and redirects < _MAX_REDIRECTS:
            target = reply.url().resolved(redir)
            reply.deleteLater()
            req2 = _make_request(target.toString())
            reply = nam.get(req2)

            timer.start(timeout_ms)
            loop.exec_()
            if timer.isActive():
                timer.stop()
            else:
                reply.abort()
                reply.deleteLater()
                return None, f"Timeout after {timeout_ms} ms (redirect)"
            err = reply.error()
            redirects += 1
            continue
        break

    if err != QNetworkReply.NoError:
        msg = reply.errorString()
        reply.deleteLater()
        return None, msg

    data = reply.readAll().data()
    final_url = reply.url().toString()
    reply.deleteLater()
    return data, final_url

def http_get_bytes(url: str, timeout_ms: int = _DEFAULT_TIMEOUT_MS) -> Tuple[bytes, str]:
    """
    Blocking GET via QGIS NAM. Respects QGIS SSL exceptions & proxy.
    Raises RuntimeError on failure.
    """
    data, err_or_url = _blocking_get(url, timeout_ms)
    if data is None:
        raise RuntimeError(f"Network error for {url}: {err_or_url}")
    return data, err_or_url  
