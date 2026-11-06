import 'auth_session.dart';

class DevicePairingRequest {
  const DevicePairingRequest({
    required this.requestId,
    required this.code,
    required this.secret,
    required this.expiresAt,
    required this.qrPayload,
  });

  final String requestId;
  final String code;
  final String secret;
  final DateTime expiresAt;
  final String qrPayload;
}

class ConnectedDevice {
  const ConnectedDevice({
    required this.reference,
    required this.name,
    required this.addedAt,
  });

  final String reference;
  final String name;
  final DateTime? addedAt;
}

abstract interface class DevicePairingApi {
  Future<DevicePairingRequest> startPairing({
    required String identity,
    required String credential,
    required String deviceId,
    required String deviceName,
  });

  Future<String> pairingStatus({
    required String requestId,
    required String secret,
  });

  Future<void> approvePairing({
    required AuthSession session,
    required String requestId,
    required String code,
  });

  Future<List<ConnectedDevice>> listDevices(AuthSession session);

  Future<void> renameDevice({
    required AuthSession session,
    required String deviceReference,
    required String deviceName,
  });

  Future<void> unlinkDevice({
    required AuthSession session,
    required String deviceReference,
  });
}
