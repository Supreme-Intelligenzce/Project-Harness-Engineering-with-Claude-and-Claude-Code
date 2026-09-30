---
description: Testing conventions for co-located TypeScript and React test files
paths:
  - "**/*.test.tsx"
  - "**/*.test.ts"
---

# Test file rules

- Tests must use explicit assertions for every behavior under test.
- Prefer assertions about observable behavior rather than implementation details.
- Use `expect(...)` for test assertions and make failure conditions clear from the test name.
- Keep each test focused on one behavior or one closely related behavior.
- Use deterministic test data rather than random values or current timestamps.
- Prefer shared test-data builders when multiple tests need the same complex fixture.
- Do not add snapshot tests; use explicit assertions instead.
- Do not use arbitrary `setTimeout(...)` calls to make asynchronous tests pass.
- Await asynchronous operations before asserting their results.
- Mock external services at their boundary rather than mocking internal implementation details.
- Keep test files co-located with the source file they exercise.
- Test both success and relevant failure paths for API handlers.