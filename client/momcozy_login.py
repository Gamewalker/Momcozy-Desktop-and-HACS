"""Experimental direct Momcozy login reconstructed from Android 3.3.0.

Input: local JSON with email, password, countryCode (account country).
No proxy, no redirects, no password output, no automatic credential retries.
"""
from state import DATA

import argparse
import base64
import configparser
import json
import urllib.error
import urllib.request
from pathlib import Path
from argon2.low_level import Type, hash_secret_raw

BASE = "https://app-api.mcozycloud.com"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def password_hash(password):
    raw = hash_secret_raw(password.encode("utf-8"),
        base64.b64decode("5waV6ARzSxRgap4h"), time_cost=2,
        memory_cost=4096, parallelism=1, hash_len=32, type=Type.ID, version=19)
    return base64.b64encode(raw).decode("ascii")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("credentials", type=Path)
    parser.add_argument("--country", default="DE")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    source = args.credentials.read_text(encoding="utf-8-sig")
    if source.lstrip().startswith("{"):
        credentials = json.loads(source)
    else:
        ini = configparser.ConfigParser(interpolation=None)
        ini.read_string(source if source.lstrip().startswith("[") else "[login]\n" + source)
        section = ini[ini.sections()[0]]
        credentials = {"email": section["USERNAME"].strip(),
                       "password": section["PASSWORD"], "countryCode": args.country}
    country = credentials["countryCode"]
    if not isinstance(country, str) or not country:
        raise ValueError("countryCode missing")
    headers = {"Content-Type": "application/json", "Client": "Android",
        "Version": "3.3.0", "X-COZY-APPID": "momcozy-0719",
        "CountryCode": country, "Language": "de", "ZoneId": "Europe/Berlin"}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def call(path, body=None):
        req = urllib.request.Request(BASE + path,
            data=None if body is None else json.dumps(body).encode(), headers=headers)
        try:
            with opener.open(req, timeout=25) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"HTTP {error.code}; no automatic retry") from None

    body = {"type": 1, "email": credentials["email"], "phone": "",
            "password": password_hash(credentials["password"]),
            "platForm": "BREAST_PUMP", "remember": 0}
    result = (json.loads((DATA/"login-response.private.json").read_text())
              if args.resume else call("/api/app/user/login/v3", body))
    (DATA/"login-response.private.json").write_text(json.dumps(result), encoding="utf-8")
    data = result.get("result", result.get("data", result))
    if not isinstance(data, dict) or not data.get("token"):
        code = result.get("code")
        print("Login not completed; numeric server code:",
              code if isinstance(code, int) else "unavailable")
        return 1
    headers["authorization"] = "Bearer " + data["token"]
    tuya = call("/api/app/third/tuya/user")
    output = (DATA/"direct-session.private.json")
    output.write_text(json.dumps({"base": BASE, "login": data, "tuya": tuya}),
                      encoding="utf-8")
    print("Momcozy login succeeded; Tuya response stored locally, no secrets printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
