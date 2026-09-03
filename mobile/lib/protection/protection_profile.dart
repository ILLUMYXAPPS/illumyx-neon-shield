/// UI-safe mirror of the server protection-profile contract.
///
/// Profiles are configuration only. They do not perform matching, remote
/// access, or enforcement. The server/evidence engine remains authoritative.
class ProtectionProfile {
  const ProtectionProfile({
    required this.key,
    required this.name,
    required this.description,
    required this.types,
    required this.evidence,
  });

  final String key;
  final String name;
  final String description;
  final List<String> types;
  final List<String> evidence;
}

const protectionProfiles = <ProtectionProfile>[
  ProtectionProfile(
    key: 'music_audio',
    name: 'Music & Audio',
    description: 'Protect recordings, podcasts and audio files.',
    types: ['audio'],
    evidence: ['audio', 'metadata', 'transcript'],
  ),
  ProtectionProfile(
    key: 'documents',
    name: 'Documents',
    description: 'Protect important documents and text files.',
    types: ['documents'],
    evidence: ['fingerprint', 'text', 'metadata'],
  ),
  ProtectionProfile(
    key: 'images',
    name: 'Images & Artwork',
    description: 'Protect photographs, artwork and image files.',
    types: ['images'],
    evidence: ['fingerprint', 'visual', 'metadata'],
  ),
  ProtectionProfile(
    key: 'video',
    name: 'Video',
    description: 'Protect video files and associated metadata.',
    types: ['video'],
    evidence: ['fingerprint', 'visual', 'audio', 'metadata'],
  ),
  ProtectionProfile(
    key: 'projects',
    name: 'Projects & Code',
    description: 'Protect project files and source code.',
    types: ['projects'],
    evidence: ['fingerprint', 'structure', 'metadata'],
  ),
  ProtectionProfile(
    key: 'custom',
    name: 'Custom Files',
    description: 'Protect a user-selected collection of files.',
    types: ['custom'],
    evidence: ['fingerprint', 'metadata'],
  ),
];

ProtectionProfile profileForKey(String key) {
  return protectionProfiles.firstWhere(
    (profile) => profile.key == key,
    orElse: () => throw ArgumentError('Unknown protection profile: $key'),
  );
}
