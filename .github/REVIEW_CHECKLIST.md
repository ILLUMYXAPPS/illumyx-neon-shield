# Neon Shield review-readiness checklist

Use this checklist when preparing or triaging pull requests. GitHub's active repository ruleset remains the source of truth.

## Author readiness

- [ ] One clear purpose; overlapping changes have been identified.
- [ ] PR is a draft until implementation and validation are ready.
- [ ] Summary, scope, security impact, tests, and rollout notes are complete.
- [ ] Relevant regression and fail-closed tests are included.
- [ ] Evidence states which checks ran and clearly labels anything not validated.
- [ ] No secrets or customer data are present.

## Required merge gates

Verify the live ruleset and PR status; do not assume a green CI badge is sufficient.

- [ ] Two eligible human approvals are recorded.
- [ ] Required code-owner approval is recorded.
- [ ] The latest reviewable push has approval from someone other than the pusher.
- [ ] All review conversations are resolved.
- [ ] Required CodeQL/security checks pass.
- [ ] Commits meet signature and linear-history requirements.
- [ ] Any applicable deployment, migration, staging, or release evidence is complete.

## Reviewer readiness and ownership

- Request review only from people who have agreed and are eligible to review.
- Required code owners must have repository write access under GitHub's rules. Do not add fictional owners or assign ownership without agreement.
- Keep reviewers independent of the change author.
- If the code-owner requirement cannot be met, treat it as a blocking governance issue. Do not disable the rule merely to make a PR mergeable.

## Triage of existing pull requests

1. Group PRs by the same feature or security finding.
2. Identify dependencies and superseded implementations.
3. Keep incomplete work in draft state.
4. Before closing a duplicate, verify that its unique fixes and tests are present in the surviving PR.
5. Do not merge or close security-sensitive work solely to reduce the open-PR count.
6. For audit-chain, authentication, database, or release changes, track reviewer findings and provider-specific validation explicitly.
