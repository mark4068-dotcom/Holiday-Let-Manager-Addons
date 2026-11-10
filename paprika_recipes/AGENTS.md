# Paprika Recipes project instructions

## Scope and source

These instructions apply to `paprika_recipes/`. The canonical source is this folder in `mark4068-dotcom/Holiday-Let-Manager-Addons`. Do not continue development in the old ChatGPT workspace. Follow the repository's `REPOSITORY_POLICY.md` as well.

## Standing order: end-of-session handover

The user explicitly requested this workflow on 10 November 2026. At the end of every work session on this project:

1. Write a dated Markdown report under `session-reports/`, using `YYYY-MM-DD-NN-topic.md`. Use Europe/London dates and times. Add a new report for each session; preserve previous reports.
2. Make the report sufficient to reconstruct a lost or corrupted chat: record the objective, user instructions and decisions, implemented changes, relevant files, architecture, commands needed to resume, checks and their actual outcomes, blockers, outstanding user actions, and the next steps. Distinguish implemented, verified, proposed, and deployed work. Include branch and relevant commit references; report any remaining uncommitted work.
3. Update relevant local repository documents to match the actual state: README, architecture/operations notes, changelog/version metadata when applicable, and `session-reports/README.md` with the latest report and a concise resume point. Update parent repository documentation when the change affects its users.
4. Review the working tree, run checks appropriate to the changes and repository policy, and commit all project changes and the session report. Include other changes made in this session within its authorised scope; never silently include unrelated pre-existing work.
5. Push the resulting commits to the project's current authorised GitHub branch. The user has given standing authorisation for these project documentation updates, commits and pushes; do not ask again merely because a session has ended. Tool-required filesystem/network approval still applies. Do not force-push, merge to the default branch, release or deploy without the corresponding authorisation.
6. Verify the push succeeded and finish with a concise status, the report link, branch/commit, and any blocker or required user action. If a check, commit or push fails, record and disclose it rather than claiming completion.

Never commit recipe exports, databases, credentials, private recipe contents, logs containing secrets, or generated caches. The session report must not duplicate those materials. A report cannot include its own final commit hash without a further commit: record the preceding commit and branch in the report and give the final documentation commit hash in the final chat response. Do not create recursive report-only commits to insert that hash.

## Resuming after context loss

Read this file, `session-reports/README.md`, the latest session report, the project README and the parent `REPOSITORY_POLICY.md`. Check the actual Git status/branch and runtime state before acting. Git is the source of truth; reports describe the state at the end of their session.
