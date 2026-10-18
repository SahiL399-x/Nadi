# Regenerating shared types
1. Start the API: `docker compose -f infra/docker-compose.yml up -d api`
2. From `packages/shared-types`: `npm install && npm run gen`
3. Commit the updated `src/types.ts`.
The frozen hand-written contract types also live in ProjectPlan.md §9; the generated
file must stay compatible with them.
