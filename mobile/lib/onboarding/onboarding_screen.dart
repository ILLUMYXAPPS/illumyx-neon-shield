import 'package:flutter/material.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key, required this.onComplete});

  final VoidCallback onComplete;

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  int _step = 0;

  static const _steps = <_OnboardingStep>[
    _OnboardingStep(
      icon: Icons.shield_rounded,
      title: 'Your digital space, protected.',
      body: 'Neon Shield brings your security posture into one clear, private-first experience.',
      detail: 'We will guide you through the setup without changing the security rules that protect your account.',
    ),
    _OnboardingStep(
      icon: Icons.person_outline_rounded,
      title: 'Secure account sign-in',
      body: 'When a verified HTTPS authentication endpoint is configured, account sign-in is checked by the server.',
      detail: 'Production mode stays locked when the authentication endpoint is missing or invalid. Local setup is not sign-in.',
    ),
    _OnboardingStep(
      icon: Icons.verified_user_outlined,
      title: 'Server-checked device trust',
      body: 'The app asks the configured authentication service to verify whether this device is trusted.',
      detail: 'The local device identifier is only a correlation value, not device attestation or proof of trust.',
    ),
    _OnboardingStep(
      icon: Icons.devices_other_rounded,
      title: 'Trusted-device controls',
      body: 'Sign-in is allowed only when the configured server reports the device as trusted.',
      detail: 'Full remote device enrollment and management still depend on the deployed backend and its policy configuration.',
    ),
    _OnboardingStep(
      icon: Icons.tune_rounded,
      title: 'Finish your local setup',
      body: 'Finish setting up the Neon Shield mobile beta dashboard.',
      detail: 'This saves local setup state only. It does not authenticate your account or enforce file protection.',
    ),
  ];

  bool get _lastStep => _step == _steps.length - 1;

  void _next() {
    if (_lastStep) {
      widget.onComplete();
      return;
    }
    setState(() => _step++);
  }

  void _back() {
    if (_step == 0) return;
    setState(() => _step--);
  }

  @override
  Widget build(BuildContext context) {
    final step = _steps[_step];
    final theme = Theme.of(context);

    return Scaffold(
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(22, 24, 22, 20),
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight - 44),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.shield_rounded, color: Color(0xFF21E6FF), size: 30),
                        const SizedBox(width: 10),
                        const Expanded(
                          child: Text('ILLUMYX NEON SHIELD', style: TextStyle(fontWeight: FontWeight.w800, letterSpacing: .8)),
                        ),
                        Text('${_step + 1}/${_steps.length}', style: const TextStyle(color: Color(0xFF9BA7C7))),
                      ],
                    ),
                    const SizedBox(height: 18),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(20),
                      child: LinearProgressIndicator(
                        minHeight: 5,
                        value: (_step + 1) / _steps.length,
                        backgroundColor: const Color(0xFF202944),
                      ),
                    ),
                    const SizedBox(height: 42),
                    Container(
                      padding: const EdgeInsets.all(24),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(28),
                        gradient: const LinearGradient(colors: [Color(0xFF11172A), Color(0xFF24143A)]),
                        border: Border.all(color: const Color(0xFF21E6FF).withValues(alpha: .35)),
                      ),
                      child: Column(
                        children: [
                          Container(
                            width: 86,
                            height: 86,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: const Color(0xFF21E6FF).withValues(alpha: .10),
                              border: Border.all(color: const Color(0xFF21E6FF).withValues(alpha: .5)),
                            ),
                            child: Icon(step.icon, size: 46, color: const Color(0xFF21E6FF)),
                          ),
                          const SizedBox(height: 26),
                          Text(step.title, textAlign: TextAlign.center, style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
                          const SizedBox(height: 14),
                          Text(step.body, textAlign: TextAlign.center, style: theme.textTheme.bodyLarge?.copyWith(height: 1.5)),
                          const SizedBox(height: 14),
                          Text(step.detail, textAlign: TextAlign.center, style: theme.textTheme.bodyMedium?.copyWith(color: const Color(0xFF9BA7C7), height: 1.45)),
                        ],
                      ),
                    ),
                    const SizedBox(height: 30),
                    Row(
                      children: [
                        if (_step > 0)
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _back,
                              icon: const Icon(Icons.arrow_back_rounded),
                              label: const Text('Back'),
                            ),
                          ),
                        if (_step > 0) const SizedBox(width: 12),
                        Expanded(
                          flex: 2,
                          child: FilledButton.icon(
                            onPressed: _next,
                            icon: Icon(_lastStep ? Icons.check_rounded : Icons.arrow_forward_rounded),
                            label: Text(_lastStep ? 'Complete local setup' : 'Continue'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Text(
                      'Server sign-in requires a configured HTTPS endpoint • Local beta mode does not enforce file protection',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodySmall?.copyWith(color: const Color(0xFF7682A4)),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _OnboardingStep {
  const _OnboardingStep({required this.icon, required this.title, required this.body, required this.detail});

  final IconData icon;
  final String title;
  final String body;
  final String detail;
}
