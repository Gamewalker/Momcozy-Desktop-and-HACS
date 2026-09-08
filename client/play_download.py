"""Google Play acquisition through pinned goopdl, without an Android device.

Use direct Google authentication only. Never use the dependency's shared token
dispenser, token cache or CLI (which prints the long-lived account token).
"""
import base64
import gzip
import hashlib
import hmac
from urllib.parse import urlsplit
import urllib.request
import zipfile

from setup_errors import SetupError

PACKAGE = "com.lute.momcozy"
VERSION = "3.3.0"
# Read from the manifest of the previously verified official 3.3.0 package.
VERSION_CODE = 30300
NATIVE = "lib/arm64-v8a/libthing_security_algorithm.so"
MAX_APK = 768 * 1024 * 1024


def google_url(url):
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if (parsed.scheme != "https" or parsed.username or parsed.password
            or parsed.port not in (None, 443)
            or not any(host.endswith("." + suffix) or host == suffix
                       for suffix in ("google.com", "googleapis.com", "googleusercontent.com", "ggpht.com"))):
        raise SetupError("play_download", "Google Play returned an unsupported download address.")
    return url


class GoogleRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        google_url(newurl)
        result = super().redirect_request(req, fp, code, msg, headers, newurl)
        # Delivery cookies must not be forwarded to a different host.
        if result and urlsplit(req.full_url).hostname != urlsplit(newurl).hostname:
            result.remove_header("Cookie")
        return result


def download_file(item, destination, cookies=()):
    size = item.download_size if hasattr(item, "download_size") else item.size
    url = getattr(item, "download_url", "") or getattr(item, "url", "")
    compressed = not bool(url)
    url = google_url(url or item.gzipped_url)
    algorithm, encoded = ("sha256", item.sha256) if item.sha256 else ("sha1", item.sha1)
    try:
        digest = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
    except (ValueError, TypeError):
        digest = b""
    if not 0 < size <= MAX_APK or len(digest) != hashlib.new(algorithm).digest_size:
        raise SetupError("play_integrity", "Google Play did not provide valid size/checksum metadata.")
    headers = {"Accept-Encoding": "identity"}
    if cookies:
        headers["Cookie"] = "; ".join(c["name"] + "=" + c["value"] for c in cookies)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), GoogleRedirect())
    partial = destination.with_suffix(".part")
    calculated, written = hashlib.new(algorithm), 0
    try:
        with opener.open(urllib.request.Request(url, headers=headers), timeout=45) as response:
            source = gzip.GzipFile(fileobj=response) if compressed else response
            with partial.open("wb") as output:
                while chunk := source.read(min(1024 * 1024, size - written + 1)):
                    written += len(chunk)
                    if written > size:
                        raise SetupError("play_integrity", "Downloaded APK exceeds its declared size.")
                    calculated.update(chunk)
                    output.write(chunk)
        if written != size or not hmac.compare_digest(calculated.digest(), digest):
            raise SetupError("play_integrity", "Downloaded APK failed its Google Play checksum.")
        partial.replace(destination)
    finally:
        partial.unlink(missing_ok=True)


def authenticate(request):
    from goopdl.auth import _direct_auth
    mode = request.get("playAuth", "browser")
    if mode == "browser":
        from goopdl.browser_oauth import capture_oauth_credentials, BrowserOAuthError
        from goopdl.aastoken import fetch_aas_token
        try:
            email, oauth = capture_oauth_credentials(timeout=240)
        except BrowserOAuthError:
            raise SetupError("play_browser", "Google sign-in did not finish. Install Chrome/Edge/Chromium/Brave or use your own AAS token.") from None
        token = fetch_aas_token(email, oauth)
    elif mode == "token":
        email, token = request.get("playEmail", "").strip(), request.get("playToken", "").strip()
        if "@" not in email or not token:
            raise SetupError("play_credentials", "Enter the Google account email and AAS token.")
    else:
        raise SetupError("invalid_request", "Unknown Google Play authentication method.")
    # Explicit arguments avoid silently using inherited GOOPDL_* credentials.
    result = _direct_auth(email, token, arch="arm64", country="DE", proxy=None, profile_name=None)
    if not result:
        raise SetupError("play_auth", "Google Play authentication failed.")
    return result


def acquire(request, stage):
    """Return locally validated base/ARM64 inputs; never return account material."""
    from goopdl import api
    from goopdl.aastoken import AASTokenError
    from goopdl.auth import DirectAuthError
    from loguru import logger
    from androguard.core.apk import APK
    logger.remove()
    try:
        auth = authenticate(request)
        details = api.get_details(PACKAGE, auth, country="DE")
        if details.package != PACKAGE:
            raise SetupError("play_version", "Google Play returned a different package.")
        # The catalog may advertise a newer build. Request only our verified
        # version; historical delivery is not guaranteed by Google.
        delivery_token = api.purchase(PACKAGE, VERSION_CODE, auth, country="DE")
        delivery = api.get_delivery(PACKAGE, VERSION_CODE, auth, country="DE", delivery_token=delivery_token)
        if delivery.version_code and delivery.version_code != VERSION_CODE:
            raise SetupError("play_version", "Google Play returned a different version.")
        base = stage / "play-base.apk"
        download_file(delivery, base, delivery.cookies)
        parsed = APK(str(base))
        if (parsed.get_package() != PACKAGE or parsed.get_androidversion_name() != VERSION
                or str(parsed.get_androidversion_code()) != str(VERSION_CODE)):
            raise SetupError("play_version", "The APK manifest does not match the requested Momcozy version.")
        with zipfile.ZipFile(base) as archive:
            if NATIVE in archive.namelist():
                return base, base
        candidates = [s for s in delivery.splits if "arm64" in s.name.lower()]
        if len(candidates) != 1:
            raise SetupError("apk_unsupported", "Google Play did not return a unique ARM64 split.")
        arm = stage / "play-arm64.apk"
        download_file(candidates[0], arm)
        split = APK(str(arm))
        if (split.get_package() != PACKAGE
                or str(split.get_androidversion_code()) != str(VERSION_CODE)):
            raise SetupError("play_version", "The ARM64 split does not match the base APK.")
        with zipfile.ZipFile(arm) as archive:
            if NATIVE not in archive.namelist():
                raise SetupError("apk_unsupported", "The ARM64 split lacks the required library.")
        return base, arm
    except SetupError:
        raise
    except (AASTokenError, DirectAuthError, api.AuthExpiredError):
        raise SetupError("play_auth", "Google rejected the sign-in or the session expired. Sign in again.") from None
    except api.RateLimitedError:
        raise SetupError("play_rate_limit", "Google Play is rate limiting this request. Try again later.") from None
    except api.AppNotAvailableError:
        raise SetupError("play_unavailable", "Momcozy is unavailable for this Google account/device region.") from None
    except api.VersionUnavailableError:
        raise SetupError("play_version", "Google Play does not deliver the supported Momcozy 3.3.0 build 30300 for this account/device.") from None
    except Exception:
        raise SetupError("play_download", "Google Play download failed. Check connectivity and account availability.") from None
