import 'dart:io';

import 'package:device_info_plus/device_info_plus.dart';
import 'package:flutter/material.dart';
import 'package:network_info_plus/network_info_plus.dart';

import '../../security/security_service.dart';

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
  final SecurityService security = SecurityService();

  bool loading = true;
  String device = 'Checking device…';
  String network = 'Checking network…';
  String platformStatus = 'Checking platform…';
  String securityStatus = 'Security policy ready';

  @override
  void initState() {
    super.initState();
    refresh();
  }

  Future<void> refresh() async {
    if (!mounted) return;
    setState(() => loading = true);

    final info = DeviceInfoPlugin();
    final wifi = NetworkInfo();

    var nextDevice = 'Device details unavailable';
    var nextNetwork = 'Network details unavailable';
    var nextPlatformStatus = 'Platform details unavailable';

    try {
      if (Platform.isAndroid) {
        final d = await info.androidInfo;
        nextDevice = '${d.manufacturer} ${d.model}';
        nextPlatformStatus = 'Android ${d.version.release}';
      } else if (Platform.isIOS) {
        final d = await info.iosInfo;
        nextDevice = d.name;
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
      network = nextNetwork;
      platformStatus = nextPlatformStatus;
      securityStatus = snapshot.ownerInitialized
          ? 'Owner initialized • ${snapshot.trustedDeviceCount} trusted device(s)'
          : 'Owner setup required';
      loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
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
                'Access-control policy is owned by the application security service.'),
            _card(Icons.phone_iphone_rounded, 'DEVICE', device, 'Local device identification only.'),
            _card(Icons.shield_outlined, 'PLATFORM', platformStatus, 'Security capabilities follow iOS and Android permission boundaries.'),
            _card(Icons.wifi_rounded, 'NETWORK', network, 'Network information is shown only when the operating system permits access.'),
            _card(Icons.lock_outline_rounded, 'PRIVACY', 'Local-first', 'Neon Shield does not need your passwords or remote-device access.'),
            const SizedBox(height: 12),
            const Text(
              'Mobile beta foundation. Platform-native posture checks will be added only where Apple and Android expose supported APIs.',
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
