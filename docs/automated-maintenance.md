# Automated dependency and maintenance checks

ILLUMYX Neon Shield uses Dependabot to propose weekly dependency updates for:
- GitHub Actions
- Python packages
- Dart/Flutter packages in `mobile/`

Proposed dependency updates must pass the repository's pull-request checks before they are considered for merge. The mobile checks and security regression suite also run weekly, even when no source changes have been pushed. They are scheduled before the Sunday evening health review to leave time for results to appear.

## Schedule
- Mobile analysis and Flutter tests: Sundays at 06:00 UTC (4:00 pm Brisbane time).
- Python dependency audit and security regression suite: Sundays at 06:20 UTC (4:20 pm Brisbane time).
- Dependabot dependency update PRs: weekly, according to `.github/dependabot.yml`.

## Safety rules
- Updates are proposed through pull requests; this workflow does not auto-merge dependencies or deploy releases.
- A passing CI run is necessary but does not replace review, device testing, or independent security assessment.
- Scheduled workflow runs can be inspected in the repository's Actions tab.
