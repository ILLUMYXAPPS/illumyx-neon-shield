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
      title: 'Neon Shield',
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

  int get securityScore {
    final snapshot = security.snapshot();
    var score = 70;
    if (snapshot.ownerInitialized) score += 10;
    if (snapshot.trustedDeviceCount > 0) score += 10;
    if (snapshot.securityEventCount == 0) score += 10;
    return score.clamp(0, 100);
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
    } catch (_) {}

    try {
      final name = await wifi.getWifiName();
      nextNetwork = name == null || name.isEmpty
          ? 'Wi-Fi name unavailable'
          : 'Wi-Fi: $name';
    } catch (_) {}

    if (!mounted) return;
    final snapshot = security.snapshot();
    setState(() {
      device = nextDevice;
      deviceId = nextDeviceId;
      network = nextNetwork;
      platformStatus = nextPlatformStatus;
      securityStatus = snapshot.ownerInitialized
          ? 'Protected • ${snapshot.trustedDeviceCount} trusted device(s)'
          : 'Action required • owner setup needed';
      loading = false;
    });
  }

  Future<void> initializeOwner() async {
    try {
      await security.initializeOwner();
      await refresh();
    } catch (error) {
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
      setState(() => securityStatus = 'Protected • $recognisedIphoneLabel recognised');
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
            : 'Geo trace captured • ${trace.latitude.toStringAsFixed(5)}, ${trace.longitude.toStringAsFixed(5)} • ±${trace.accuracyMeters.toStringAsFixed(0)}m';
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
    final snapshot = security.snapshot();
    final events = security.recentSecurityEvents.take(5).toList();
    final canRecognise = Platform.isIOS && device.contains('iPhone 16 Pro');

    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('NEON SHIELD', style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 1.2)),
            Text('ILLUMYX • Mobile Security', style: TextStyle(fontSize: 12, color: Color(0xFF21E6FF))),
          ],
        ),
        actions: [
          IconButton(onPressed: loading ? null : refresh, icon: const Icon(Icons.refresh_rounded)),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: refresh,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(18, 8, 18, 28),
          children: [
            _hero(),
            const SizedBox(height: 14),
            _statusCard(),
            const SizedBox(height: 14),
            _sectionTitle('SECURITY ACTIVITY', 'Your latest local security events'),
            const SizedBox(height: 8),
            if (events.isEmpty) _emptyEvents() else ...events.map(_eventTile),
            const SizedBox(height: 14),
            _sectionTitle('PROTECTION', 'Your security controls'),
            const SizedBox(height: 8),
            _card(Icons.phone_iphone_rounded, 'DEVICE', device, 'Platform-provided device identity.'),
            _card(Icons.verified_user_outlined, 'TRUST', securityStatus, 'Only recognised device identifiers can satisfy the local trust check.'),
            _card(Icons.shield_outlined, 'PLATFORM', platformStatus, 'Security capabilities follow OS permission boundaries.'),
            _card(Icons.wifi_rounded, 'NETWORK', network, 'Network information is shown only when the operating system permits access.'),
            _card(Icons.location_on_outlined, 'GEO TRACER', geoStatus, 'Foreground location only. OS permission is required before a trace is captured.'),
            const SizedBox(height: 8),
            if (!snapshot.ownerInitialized)
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
            const SizedBox(height: 18),
            _premiumCard(),
            const SizedBox(height: 16),
            const Text(
              'Neon Shield is calm by design: protection status first, useful events second, controls when you need them. Authentication and unknown-device enforcement must remain server-side before issuing sessions or tokens.',
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
          borderRadius: BorderRadius.circular(26),
          gradient: const LinearGradient(colors: [Color(0xFF11172A), Color(0xFF24143A)]),
          border: Border.all(color: const Color(0xFF21E6FF).withValues(alpha: .45)),
        ),
        child: Row(
          children: [
            const Icon(Icons.shield_rounded, size: 60, color: Color(0xFF21E6FF)),
            const SizedBox(width: 18),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    loading ? 'CHECKING…' : security.snapshot().ownerInitialized ? "YOU'RE PROTECTED" : 'ACTION REQUIRED',
                    style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w900),
                  ),
                  const SizedBox(height: 6),
                  const Text('Neon Shield is watching the doors.', style: TextStyle(color: Color(0xFFFF38D1), fontWeight: FontWeight.w600)),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _statusCard() => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(color: const Color(0xFF11172A), borderRadius: BorderRadius.circular(22)),
        child: Row(
          children: [
            SizedBox(
              width: 86,
              height: 86,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  CircularProgressIndicator(value: securityScore / 100, strokeWidth: 7, backgroundColor: const Color(0xFF242B43)),
                  Text('$securityScore', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
                ],
              ),
            ),
            const SizedBox(width: 18),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('SECURITY SCORE', style: TextStyle(color: Color(0xFF9BA7C7), fontSize: 12, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 5),
                  Text(securityScore >= 90 ? 'Excellent protection' : 'Complete setup to improve protection', style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 5),
                  Text('${security.snapshot().trustedDeviceCount} trusted device(s) • ${security.snapshot().securityEventCount} event(s)', style: const TextStyle(color: Color(0xFF9BA7C7))),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _sectionTitle(String title, String detail) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: 1.1)),
          const SizedBox(height: 3),
          Text(detail, style: const TextStyle(color: Color(0xFF9BA7C7), fontSize: 12)),
        ],
      );

  Widget _emptyEvents() => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(color: const Color(0xFF11172A), borderRadius: BorderRadius.circular(18)),
        child: const Row(
          children: [
            Icon(Icons.check_circle_outline_rounded, color: Color(0xFF21E6FF)),
            SizedBox(width: 12),
            Expanded(child: Text('No security events need your attention.', style: TextStyle(fontWeight: FontWeight.w600))),
          ],
        ),
      );

  Widget _eventTile(SecurityEvent event) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: const Color(0xFF11172A), borderRadius: BorderRadius.circular(16)),
        child: Row(
          children: [
            Icon(event.type == 'unsupported_login' ? Icons.block_rounded : Icons.check_circle_rounded, color: event.type == 'unsupported_login' ? const Color(0xFFFF38D1) : const Color(0xFF21E6FF)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(event.type == 'unsupported_login' ? 'Unknown device blocked' : event.type, style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 3),
                  Text(event.reason, style: const TextStyle(color: Color(0xFF9BA7C7), fontSize: 12)),
                ],
              ),
            ),
            Text(_timeLabel(event.timestamp), style: const TextStyle(color: Color(0xFF9BA7C7), fontSize: 11)),
          ],
        ),
      );

  String _timeLabel(DateTime timestamp) {
    final local = timestamp.toLocal();
    final hour = local.hour.toString().padLeft(2, '0');
    final minute = local.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
  }

  Widget _premiumCard() => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(22),
          gradient: const LinearGradient(colors: [Color(0xFF24143A), Color(0xFF11172A)]),
          border: Border.all(color: const Color(0xFFFF38D1).withValues(alpha: .35)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('NEON SHIELD PREMIUM', style: TextStyle(color: Color(0xFFFF38D1), fontWeight: FontWeight.w900, letterSpacing: 1)),
            const SizedBox(height: 8),
            const Text('Take your protection further.', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            const Text('Advanced alerts, deeper device visibility and expanded security controls.', style: TextStyle(color: Color(0xFF9BA7C7), height: 1.4)),
            const SizedBox(height: 14),
            OutlinedButton(onPressed: () => _showMessage('Premium storefront coming in the subscription release.'), child: const Text('EXPLORE PREMIUM')),
          ],
        ),
      );

  Widget _card(IconData icon, String title, String value, String detail) => Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(17),
        decoration: BoxDecoration(color: const Color(0xFF11172A), borderRadius: BorderRadius.circular(18)),
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
                  Text(value, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text(detail, style: const TextStyle(color: Color(0xFF9BA7C7), height: 1.35)),
                ],
              ),
            ),
          ],
        ),
      );
}
