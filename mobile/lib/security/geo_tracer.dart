import 'package:geolocator/geolocator.dart';

/// Privacy-first foreground geo tracer.
///
/// Location is collected only after the user grants the operating system's
a/// location permission. This service intentionally performs one-shot
/// foreground reads; continuous/background tracking requires a separate,
/// explicit product decision and platform configuration.
class GeoTrace {
  const GeoTrace({
    required this.latitude,
    required this.longitude,
    required this.accuracyMeters,
    required this.capturedAt,
  });

  final double latitude;
  final double longitude;
  final double accuracyMeters;
  final DateTime capturedAt;
}

class GeoTracer {
  Future<bool> ensurePermission() async {
    if (!await Geolocator.isLocationServiceEnabled()) return false;

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    return permission == LocationPermission.whileInUse ||
        permission == LocationPermission.always;
  }

  Future<GeoTrace?> captureCurrentLocation() async {
    if (!await ensurePermission()) return null;

    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
      ),
    );

    return GeoTrace(
      latitude: position.latitude,
      longitude: position.longitude,
      accuracyMeters: position.accuracy,
      capturedAt: position.timestamp,
    );
  }
}
