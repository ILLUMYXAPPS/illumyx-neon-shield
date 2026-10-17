# Neon Shield ownership and review model

## Software owner

The repository owner, `@ILLUMYXAPPS`, owns the Neon Shield software project and is responsible for:

- Product vision, scope, priorities, and roadmap.
- Directing development and deciding which work is accepted.
- Coordinating contributors, technical review, and release readiness.
- Making release decisions after the applicable quality, security, and operational gates are met.

Ownership of the software does not mean every change is self-approved. The owner remains accountable for ensuring that required independent reviews and checks are completed.

## Independent review

The active GitHub ruleset currently requires two approving reviews, code-owner review, approval of the latest reviewable push by someone other than the pusher, resolution of review conversations, CodeQL checks, signed commits, and linear history.

- A pull-request author must not approve their own change.
- Automated checks and automated review comments do not substitute for the required eligible human approvals.
- Reviewers must be real people who are willing and qualified to review the change.
- Do not list a person or team in `CODEOWNERS` until they have the necessary repository write access and have agreed to take on that responsibility.
- Do not weaken or bypass the ruleset merely to make a pull request mergeable.

## Code-owner setup status

A valid, operational `.github/CODEOWNERS` entry has not yet been configured by this documentation change. The repository needs an agreed code owner with write access before a reliable code-owner assignment can be made.

Do not use the software owner's account as a substitute for an independent reviewer on changes authored by that same account. Do not invent usernames or assume a public commenter has write access.

## Readiness procedure

1. Identify a willing independent reviewer and grant only the repository access needed for the role.
2. Confirm the reviewer is eligible under the repository's current ruleset and can provide a formal GitHub approval.
3. Add the agreed owner to `.github/CODEOWNERS` in a separate reviewed change, including ownership of the `.github/CODEOWNERS` file itself.
4. Verify that a test pull request correctly requests code-owner review and that required approvals are recognised.
5. Keep all required gates enabled and resolve any outstanding review conversations before merge.
