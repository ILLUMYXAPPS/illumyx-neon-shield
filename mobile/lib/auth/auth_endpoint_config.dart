/// Validates the endpoint supplied to the production app configuration.
///
/// The generic HTTP adapter permits loopback HTTP for isolated local tests.
/// The shipped app must be stricter: its configured endpoint is always HTTPS,
/// including when the host happens to be localhost. Empty configuration returns
/// null so bootstrap can keep dashboard access locked.
Uri? parseProductionAuthEndpoint(String value) {
  final endpoint = value.trim();
  if (endpoint.isEmpty) return null;

  final uri = Uri.tryParse(endpoint);
  if (uri == null ||
      uri.scheme != 'https' ||
      uri.host.isEmpty ||
      uri.userInfo.isNotEmpty ||
      uri.hasQuery ||
      uri.hasFragment) {
    throw const FormatException(
      'Neon Shield requires a valid HTTPS auth base URL without credentials, query, or fragment.',
    );
  }
  return uri;
}
