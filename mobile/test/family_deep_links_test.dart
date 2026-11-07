import 'package:flutter_test/flutter_test.dart';
import 'package:illumyx_neon_shield/family/family_deep_links.dart';

void main() {
  test('creates a tappable Family invitation URI', () {
    final uri = FamilyInvitationLink.create('secure-code-123');
    expect(uri.scheme, 'neonshield');
    expect(uri.host, 'family');
    expect(uri.path, '/invite');
    expect(uri.queryParameters['code'], 'secure-code-123');
  });

  test('extracts invitation code from a supported URI', () {
    final code = FamilyInvitationLink.codeFrom(
      Uri.parse('neonshield://family/invite?code=secure-code-123'),
    );
    expect(code, 'secure-code-123');
  });

  test('rejects unsupported schemes, paths, hosts and missing codes', () {
    expect(
      FamilyInvitationLink.codeFrom(
        Uri.parse('https://family.example/invite?code=abc'),
      ),
      isNull,
    );
    expect(
      FamilyInvitationLink.codeFrom(
        Uri.parse('neonshield://other/invite?code=abc'),
      ),
      isNull,
    );
    expect(
      FamilyInvitationLink.codeFrom(
        Uri.parse('neonshield://family/other?code=abc'),
      ),
      isNull,
    );
    expect(
      FamilyInvitationLink.codeFrom(
        Uri.parse('neonshield://family/invite'),
      ),
      isNull,
    );
    expect(
      FamilyInvitationLink.codeFrom(
        Uri.parse('neonshield://family/invite?code=%20%20'),
      ),
      isNull,
    );
  });

  test('rejects empty invitation code when creating a link', () {
    expect(() => FamilyInvitationLink.create(' '), throwsArgumentError);
  });
}
