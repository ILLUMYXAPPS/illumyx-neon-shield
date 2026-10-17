# Contributing to Neon Shield

Thank you for helping improve Neon Shield. Security-sensitive changes must be easy to understand, reproduce, and independently review.

## Software ownership

The repository owner, `@ILLUMYXAPPS`, owns the Neon Shield software project and is responsible for product direction, development priorities, and release decisions. This ownership does not replace independent code review or permit self-approval of pull requests. Changes authored by the owner must still satisfy the same required review and status-check gates as other changes.

## Before opening a pull request

- Keep each pull request focused on one change or tightly related set of changes.
- Search open pull requests for overlapping work before starting a new implementation.
- Explain the problem, the proposed change, risks, and any migration or rollout implications.
- Add regression tests for bugs and security findings. Include negative tests for fail-closed behaviour where relevant.
- Run the applicable tests and security checks locally when possible; report exactly what was run and what could not be run.
- Never include secrets, personal data, production credentials, or real customer data in commits, tests, logs, or screenshots.
- Do not claim production validation based only on disposable CI infrastructure.

## Review and merge policy

The repository's active GitHub ruleset is authoritative. Contributors must not bypass, weaken, or work around required reviews or checks.

Current merge expectations include:

- Two approving reviews from eligible reviewers.
- Required code-owner approval when applicable.
- Approval of the latest reviewable push by someone other than the pusher.
- All review conversations resolved.
- Required CodeQL and other configured checks passing.
- Signed commits and linear history.
- Any required migration, staging, or release evidence documented before deployment.

Authors must not approve their own pull requests. A comment, automated review, passing CI run, or informal offer to review is not a substitute for a submitted GitHub approval from an eligible reviewer.

## Pull request lifecycle

- Open as a draft while implementation or validation is incomplete.
- Mark ready for review only when the description, tests, and evidence are prepared.
- Respond to every substantive review comment and link the corresponding fix or test.
- If a new commit changes reviewed code, request a fresh review as required by repository policy.
- Do not merge while a required approval, check, conversation resolution, or external validation remains outstanding.

## Production and database changes

- Include migration ordering, rollback considerations, and compatibility notes.
- Distinguish unit tests, disposable integration tests, staging validation, and production evidence.
- Never treat CI database success as proof that the eventual managed database provider has been validated.
- Follow the documented release gate and obtain independent review before deployment.
