/// Product specification for the finished Neon Shield dashboard.
///
/// This keeps the UI direction explicit while the mobile beta is stabilized.
/// The production dashboard should expose these sections in this order:
///
/// 1. Protection hero
///    - YOU'RE PROTECTED when the local security state is healthy.
///    - ACTION REQUIRED when owner/device setup is incomplete.
///    - THREAT DETECTED for high-priority security events.
///
/// 2. Security score
///    - 0..100 summary derived from real security state.
///    - Never present a reassuring score when required backend checks fail.
///
/// 3. Security activity timeline
///    - Trusted-device verification.
///    - Unsupported-device attempts.
///    - Device enrolment/removal.
///    - Security setting changes.
///    - Geo Tracer events.
///    - Newest events first, with clear severity.
///
/// 4. Protection controls
///    - Trusted devices.
///    - Geo Tracer.
///    - Account protection.
///    - Network posture.
///
/// 5. Premium entry point
///    - Explain value without fear-based copy or dark patterns.
///    - Premium: advanced alerts, deeper device visibility, expanded controls.
///    - Family: household protection across supported members/devices.
///
/// 6. First-run experience
///    - Welcome: "Your personal security shield."
///    - Explain permissions before requesting them.
///    - Verify the current device.
///    - Offer Geo Tracer permission with a plain-language explanation.
///    - Finish with: "YOU'RE PROTECTED" and a clear next step.
///
/// Security boundary:
/// The dashboard is a presentation layer. Unknown-device authentication,
/// session/token issuance, and other authoritative access decisions must be
/// enforced by the backend, not by UI state or local preferences.
class FinishedDashboardSpec {
  const FinishedDashboardSpec._();

  static const String protectionMessage =
      'Neon Shield is watching the doors.';
  static const String healthyState = 'YOU\'RE PROTECTED';
  static const String actionState = 'ACTION REQUIRED';
  static const String threatState = 'THREAT DETECTED';
}
