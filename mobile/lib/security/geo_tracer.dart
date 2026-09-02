import 'package:geolocator/geolocator.dart';

class GeoTrace {
  const GeoTrace({
    required this.latitude,
    required this.longitude,
    required this.accuracyMeters,
  });

  final double latitude;
  final double longitude;
  final double accuracyMeters;
}

/// Foreground-only location capture for explicitly enabled Geo Tracer events.
///
/// This class never requests background location and returns null when the OS
/// does not grant the required foreground permission or location services are
/// unavailable.
class GeoTracer {
  Future<GeoTrace?> captureCurrentLocation() async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      return null;
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever ||
        permission == LocationPermission.unableToDetermine) {
      return null;
    }

    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
      ),
    );

    return GeoTrace(
      latitude: position.latitude,
      longitude: position.longitude,
      accuracyMeters: position.accuracy,
    );
  }
}
