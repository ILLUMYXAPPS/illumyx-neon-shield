#!/usr/bin/env python3
"""Register the Neon Shield Family invitation URI scheme in generated projects."""

from __future__ import annotations

import argparse
import plistlib
import xml.etree.ElementTree as ET
from pathlib import Path

ANDROID_NS = "http://schemas.android.com/apk/res/android"
ET.register_namespace("android", ANDROID_NS)


def _android_attr(name: str) -> str:
    return f"{{{ANDROID_NS}}}{name}"


def configure_android(manifest_path: Path) -> None:
    tree = ET.parse(manifest_path)
    root = tree.getroot()
    application = root.find("application")
    if application is None:
        raise ValueError("Android manifest has no application element")

    activities = application.findall("activity")
    target = next(
        (
            activity
            for activity in activities
            if any(
                action.get(_android_attr("name")) == "android.intent.action.MAIN"
                for action in activity.findall("intent-filter/action")
            )
        ),
        None,
    )
    if target is None:
        target = next(
            (activity for activity in activities
             if activity.get(_android_attr("name"), "").endswith("MainActivity")),
            None,
        )
    if target is None:
        raise ValueError("Android manifest has no Flutter MainActivity")

    for intent_filter in target.findall("intent-filter"):
        for data in intent_filter.findall("data"):
            if (
                data.get(_android_attr("scheme")) == "neonshield"
                and data.get(_android_attr("host")) == "family"
                and data.get(_android_attr("pathPrefix")) == "/invite"
            ):
                tree.write(manifest_path, encoding="utf-8", xml_declaration=True)
                return

    intent_filter = ET.SubElement(target, "intent-filter")
    ET.SubElement(intent_filter, "action", {_android_attr("name"): "android.intent.action.VIEW"})
    ET.SubElement(intent_filter, "category", {_android_attr("name"): "android.intent.category.DEFAULT"})
    ET.SubElement(intent_filter, "category", {_android_attr("name"): "android.intent.category.BROWSABLE"})
    ET.SubElement(
        intent_filter,
        "data",
        {
            _android_attr("scheme"): "neonshield",
            _android_attr("host"): "family",
            _android_attr("pathPrefix"): "/invite",
        },
    )
    tree.write(manifest_path, encoding="utf-8", xml_declaration=True)


def configure_ios(info_path: Path) -> None:
    with info_path.open("rb") as source:
        info = plistlib.load(source)

    url_types = info.setdefault("CFBundleURLTypes", [])
    if not isinstance(url_types, list):
        raise ValueError("CFBundleURLTypes must be an array")
    for item in url_types:
        if isinstance(item, dict) and "neonshield" in item.get("CFBundleURLSchemes", []):
            return

    url_types.append(
        {
            "CFBundleURLName": "com.illumyx.illumyxapp.family-invitation",
            "CFBundleURLSchemes": ["neonshield"],
        }
    )
    with info_path.open("wb") as destination:
        plistlib.dump(info, destination, sort_keys=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--android-manifest", type=Path)
    parser.add_argument("--ios-info", type=Path)
    args = parser.parse_args()
    if not args.android_manifest and not args.ios_info:
        parser.error("provide --android-manifest and/or --ios-info")
    if args.android_manifest:
        configure_android(args.android_manifest)
        print(f"Registered neonshield://family/invite in {args.android_manifest}")
    if args.ios_info:
        configure_ios(args.ios_info)
        print(f"Registered neonshield://family/invite in {args.ios_info}")


if __name__ == "__main__":
    main()
