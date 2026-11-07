import plistlib
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from configure_family_deep_links import ANDROID_NS, configure_android, configure_ios


def android_attr(name):
    return f"{{{ANDROID_NS}}}{name}"


class FamilyDeepLinkConfigurationTests(unittest.TestCase):
    def test_android_registers_family_invitation_view_filter_idempotently(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "AndroidManifest.xml"
            manifest = (
                '<manifest xmlns:android="' + ANDROID_NS + '">'
                '<application>'
                '<activity android:name=".MainActivity">'
                '<intent-filter>'
                '<action android:name="android.intent.action.MAIN" />'
                '<category android:name="android.intent.category.LAUNCHER" />'
                '</intent-filter>'
                '</activity>'
                '</application>'
                '</manifest>'
            )
            path.write_text(manifest)

            configure_android(path)
            configure_android(path)
            root = ET.parse(path).getroot()
            activity = root.find("application/activity")
            matches = []
            for item in activity.findall("intent-filter"):
                data = item.find("data")
                if data is not None and data.get(android_attr("scheme")) == "neonshield":
                    matches.append((item, data))

            self.assertEqual(len(matches), 1)
            intent_filter, data = matches[0]
            self.assertEqual(data.get(android_attr("host")), "family")
            self.assertEqual(data.get(android_attr("pathPrefix")), "/invite")
            actions = {node.get(android_attr("name")) for node in intent_filter.findall("action")}
            categories = {node.get(android_attr("name")) for node in intent_filter.findall("category")}
            self.assertIn("android.intent.action.VIEW", actions)
            self.assertIn("android.intent.category.DEFAULT", categories)
            self.assertIn("android.intent.category.BROWSABLE", categories)

    def test_ios_registers_custom_url_scheme_idempotently(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "Info.plist"
            with path.open("wb") as output:
                plistlib.dump({"CFBundleIdentifier": "com.illumyx.illumyxapp"}, output)

            configure_ios(path)
            configure_ios(path)
            with path.open("rb") as source:
                info = plistlib.load(source)

            registrations = [
                item for item in info["CFBundleURLTypes"]
                if "neonshield" in item.get("CFBundleURLSchemes", [])
            ]
            self.assertEqual(len(registrations), 1)
            self.assertEqual(
                registrations[0]["CFBundleURLName"],
                "com.illumyx.illumyxapp.family-invitation",
            )


if __name__ == "__main__":
    unittest.main()
