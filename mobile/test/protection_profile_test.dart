import 'package:flutter_test/flutter_test.dart';

import '../lib/protection/protection_profile.dart';

void main() {
  test('profile catalog matches server contract order', () {
    expect(
      protectionProfiles.map((profile) => profile.key).toList(),
      ['music_audio', 'documents', 'images', 'video', 'projects', 'custom'],
    );
  });

  test('music audio profile exposes expected evidence', () {
    final profile = profileForKey('music_audio');

    expect(profile.name, 'Music & Audio');
    expect(profile.types, ['audio']);
    expect(profile.evidence, ['audio', 'metadata', 'transcript']);
  });

  test('unknown profile keys fail closed', () {
    expect(() => profileForKey('not-a-profile'), throwsArgumentError);
  });
}
