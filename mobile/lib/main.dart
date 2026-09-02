import 'dart:io';

import 'package:device_info_plus/device_info_plus.dart';
import 'package:flutter/material.dart';
import 'package:network_info_plus/network_info_plus.dart';

import 'security/geo_tracer.dart';
import 'security/security_service.dart';

void main() => runApp(const NeonShieldApp());

class NeonShieldApp extends StatelessWidget {
  const NeonShieldApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'ILLUMYX Neon Shield',
      theme: ThemeData.dark(useMaterial3: true).copyWith(
        scaffoldBackgroundColor: const Color(0xFF070A16),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF21E6FF),
          secondary: Color(0xFFFF38D1),
          tertiary: Color(0xFF8B5CFF),
          surface: Color(0xFF11172A),
        ),
      ),
      home: const ShieldDashboard(),
    );
  }
}

class ShieldDashboard extends StatefulWidget {
  const ShieldDashboard({super.key});

  @override
  State<ShieldDashboard> createState() => _ShieldDashboardState();
}

class _ShieldDashboardState extends State<ShieldDashboard> {
  static const String recognisedIphoneLabel = 'Aaron Paszek iPhone 16 Pro';

  final SecurityService security = SecurityService();
  final GeoTracer geoTracer = GeoTracer();

  bool loading = true;
  bool geoLoading = false;
  String device = 'Checking device…';
  String deviceId = '';
  String network = 'Checking network…';
  String platformStatus = 'Checking platform…';
  String securityStatus = 'Loading security state…';
  String geoStatus = 'Geo Tracer ready • permission required';

  @override
  void initState() {
    super.initState();
    refresh();
  }

  Future<void> refresh() async {
    if (!mounted) return;
    setState(() => loading = true);

    try {
      await security.load();
    } catch (_) {
      if (!mounted) return;
      setState(() {
        securityStatus = 'Security state unavailable';
        loading = false;
      });
      return;
    }

    final info = DeviceInfoPlugin();
    final wifi = NetworkInfo();

    var nextDevice = 'Device details unavailable';
    var nextDeviceId = '';
    var nextNetwork = 'Network details unavailable';
    var nextPlatformStatus = 'Platform details unavailable';

    try {
      if (Platform.isAndroid) {
        final d = await info.androidInfo;
        nextDevice = '${d.manufacturer} ${d.model}';
        nextDeviceId = d.id;
        nextPlatformStatus = 'Android ${d.version.release}';
      } else if (Platform.isIOS) {
        final d = await info.iosInfo;
        nextDevice = d.name;
        nextDeviceId = d.identifierForVendor ?? '';
        nextPlatformStatus = '${d.systemName} ${d.systemVersion}';
      } else {
        nextDevice = Platform.operatingSystem;
        nextPlatformStatus = 'Unsupported mobile platform';
      }
    } catch (_) {
      // Keep safe fallback values.
    }

    try {
      final name = await wifi.getWifiName();
      nextNetwork = name == null || name.isEmpty
          ? 'Wi-Fi name unavailable'
          : 'Wi-Fi: $name';
    } catch (_) {
      // Keep safe fallback value.
    }

    if (!mounted) return;
    final snapshot = security.snapshot();
    setState(() {
      device = nextDevice;
      deviceId = nextDeviceId;
      network = nextNetwork;
      platformStatus = nextPlatformStatus;
      securityStatus = snapshot.ownerInitialized
          ? 'Owner initialized • ${snapshot.trustedDeviceCount} trusted device(s)'
          : 'Owner setup required';
      loading = false;
    });
  }

  Future<void> initializeOwner() async {
    try {
      await security.initializeOwner();
      await refresh();
    } catch (error) {
      if (!mounted) return;
      _showMessage('$error');
    }
  }

  Future<void> recogniseCurrentIphone() async {
    if (!Platform.isIOS || !device.contains('iPhone 16 Pro')) {
      _showMessage('This action is only available on the iPhone 16 Pro.');
      return;
    }
    if (!security.snapshot().ownerInitialized) {
      _showMessage('Initialize the Shield owner before recognising a device.');
      return;
    }
    if (deviceId.isEmpty) {
      _showMessage('The device identity is unavailable.');
      return;
    }

    try {
      await security.addTrustedDevice(deviceId);
      if (!mounted) return;
      setState(() {
        securityStatus = 'Recognised • $recognisedIphoneLabel';
      });
    } catch (error) {
      _showMessage('$error');
    }
  }

  Future<void> captureGeo() async {
    if (geoLoading) return;
    setState(() {
      geoLoading = true;
      geoStatus = 'Requesting permitted location…';
    });

    try {
      final trace = await geoTracer.captureCurrentLocation();
      if (!mounted) return;
      setState(() {
        geoStatus = trace == null
            ? 'Location unavailable or permission not granted'
            : 'Geo trace captured • ${trace.latitude.toStringAsFixed(5)}, '
                '${trace.longitude.toStringAsFixed(5)} • ±${trace.accuracyMeters.toStringAsFixed(0)}m';
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => geoStatus = 'Geo trace failed safely');
    } finally {
      if (mounted) setState(() => geoLoading = false);
    }
  }

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final canRecognise = Platform.isIOS && device.contains('iPhone 16 Pro');

    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('ILLUMYX NEON SHIELD', style: TextStyle(fontWeight: FontWeight.w800)),
            Text('Mobile v1.0-beta', style: TextStyle(fontSize: 12, color: Color(0xFF21E6FF))),
          ],
        ),
        actions: [
          IconButton(
            onPressed: loading ? null : refresh,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: refresh,
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            _hero(),
            const SizedBox(height: 18),
            _card(Icons.lock_rounded, 'SECURITY', securityStatus,
                'Recognised-device access remains denied until owner setup and device enrolment are completed.'),
            _card(Icons.phone_iphone_rounded, 'DEVICE', device, 'Platform-provided local device identity.'),
            if (deviceId.isNotEmpty)
              _card(Icons.fingerprint_rounded, 'DEVICE ID', deviceId,
                  'Used locally for recognised-device matching; never use the display name as the trust credential.'),
            _card(Icons.shield_outlined, 'PLATFORM', platformStatus, 'Security capabilities follow iOS and Android permission boundaries.'),
            _card(Icons.wifi_rounded, 'NETWORK', network, 'Network information is shown only when the operating system permits access.'),
            _card(Icons.location_on_outlined, 'GEO TRACER', geoStatus,
                'Foreground location only. The operating system must grant permission before a trace is captured.'),
            const SizedBox(height: 6),
            if (!security.snapshot().ownerInitialized)
              FilledButton.icon(
                onPressed: loading ? null : initializeOwner,
                icon: const Icon(Icons.admin_panel_settings_outlined),
                label: const Text('INITIALIZE SHIELD OWNER'),
              ),
            if (canRecognise) ...[
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: recogniseCurrentIphone,
                icon: const Icon(Icons.verified_user_outlined),
                label: const Text('RECOGNISE AARON PASZEK IPHONE 16 PRO'),
              ),
            ],
            const SizedBox(height: 10),
            FilledButton.icon(
              onPressed: geoLoading ? null : captureGeo,
              icon: const Icon(Icons.my_location_rounded),
              label: Text(geoLoading ? 'TRACING…' : 'CAPTURE PERMITTED GEO TRACE'),
            ),
            const SizedBox(height: 12),
            const Text(
              'Mobile beta foundation. Unknown-device login enforcement and server-side security events must be enforced by the authentication backend before a session or token is issued.',
              style: TextStyle(color: Color(0xFF9BA7C7), height: 1.45),
            ),
          ],
        ),
      ),
    );
  }

  Widget _hero() => Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(24),
          gradient: const LinearGradient(
            colors: [Color(0xFF11172A), Color(0xFF24143A)],
          ),
          border: Border.all(
            color: const Color(0xFF21E6FF).withValues(alpha: .45),
          ),
        ),
        child: Row(
          children: [
            const Icon(Icons.shield_rounded, size: 58, color: Color(0xFF21E6FF)),
            const SizedBox(width: 18),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    loading ? 'Checking…' : 'Mobile Shield Ready',
                    style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Secure. Smart. Neon.',
                    style: TextStyle(color: Color(0xFFFF38D1), fontWeight: FontWeight.w600),
                  ),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _card(IconData icon, String title, String value, String detail) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: const Color(0xFF11172A),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: const Color(0xFF8B5CFF)),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontSize: 12, color: Color(0xFF9BA7C7), fontWeight: FontWeight.bold)),
                  const SizedBox(height: 5),
                  Text(value, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 5),
                  Text(detail, style: const TextStyle(color: Color(0xFF9BA7C7), height: 1.35)),
                ],
              ),
            ),
          ],
        ),
      );
}
