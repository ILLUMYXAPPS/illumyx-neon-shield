import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/auth/auth_endpoint_config.dart';

void main() {
  test('empty endpoint leaves production authentication unconfigured', () {
    expect(parseProductionAuthEndpoint(''), isNull);
    expect(parseProductionAuthEndpoint('  '), isNull);
  });

  test('accepts a valid HTTPS endpoint', () {
    expect(
      parseProductionAuthEndpoint(' https://auth.example.invalid '),
      Uri.parse('https://auth.example.invalid'),
    );
  });

  test('rejects HTTP, including loopback HTTP in app configuration', () {
    expect(() => parseProductionAuthEndpoint('http://localhost:8080'), throwsFormatException);
    expect(() => parseProductionAuthEndpoint('http://127.0.0.1:8080'), throwsFormatException);
  });

  test('rejects malformed or unsafe endpoint forms', () {
    for (final endpoint in <String>[
      'not a URL',
      'https:///missing-host',
      'https://user:password@auth.example.invalid',
      'https://auth.example.invalid?debug=true',
      'https://auth.example.invalid#fragment',
    ]) {
      expect(
        () => parseProductionAuthEndpoint(endpoint),
        throwsFormatException,
        reason: 'Should reject $endpoint',
      );
    }
  });
}
