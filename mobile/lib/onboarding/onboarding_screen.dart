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
      title: 'Secure your account',
      body: 'Your account and authentication remain governed by the existing Neon Shield security service.',
      detail: 'This step prepares the experience for your existing authentication flow. No credentials are stored in onboarding.',
    ),
    _OnboardingStep(
      icon: Icons.verified_user_outlined,
      title: 'Verify this device',
      body: 'Neon Shield treats device trust as a security boundary, not a cosmetic setting.',
      detail: 'Device verification continues through the existing security contract. Onboarding never bypasses that check.',
    ),
    _OnboardingStep(
      icon: Icons.devices_other_rounded,
      title: 'Choose trusted devices',
      body: 'Keep control of which devices can participate in your protected environment.',
      detail: 'You can review trusted-device status from the security controls after setup.',
    ),
    _OnboardingStep(
      icon: Icons.tune_rounded,
      title: 'Protection setup',
      body: 'Start with the protection experience and tune it as your needs evolve.',
      detail: 'Security-critical policy stays with the existing application and server contracts.',
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
                            label: Text(_lastStep ? 'Enter Neon Shield' : 'Continue'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Text(
                      'Privacy-first setup • Security boundaries remain enforced',
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
