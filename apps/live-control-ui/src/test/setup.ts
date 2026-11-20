import "@testing-library/jest-dom/vitest";
import { beforeEach } from "vitest";
import { createTestLocks } from "../combat/testLocks";

beforeEach(() => {
  Object.defineProperty(navigator, "locks", { configurable: true, value: createTestLocks() });
});
