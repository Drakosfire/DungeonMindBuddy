import { describe, expect, it } from "vitest";

import {
  buildSurfaceInteractionIdentity,
  encodeSurfaceInteractionInstanceKey,
  sameSurfaceInteractionIdentity,
} from "./surfaceIdentity";
import type { SurfaceInteractionInstancePart } from "./types";

describe("encodeSurfaceInteractionInstanceKey", () => {
  it("is deterministic for the same typed tuple", () => {
    const parts: SurfaceInteractionInstancePart[] = ["plan", "doc-1", 3, null, true];
    expect(encodeSurfaceInteractionInstanceKey(parts)).toBe(
      encodeSurfaceInteractionInstanceKey([...parts]),
    );
  });

  it("preserves tuple boundaries against delimiter adversaries", () => {
    const left = encodeSurfaceInteractionInstanceKey(["a", "b:c"]);
    const right = encodeSurfaceInteractionInstanceKey(["a:b", "c"]);
    expect(left).not.toBe(right);
  });

  it("preserves part types so distinct typed tuples cannot collapse", () => {
    const cases: Array<[SurfaceInteractionInstancePart, SurfaceInteractionInstancePart]> = [
      ["1", 1],
      ["true", true],
      ["null", null],
      ["0", 0],
      [0, false],
      ["", null],
    ];
    for (const [left, right] of cases) {
      expect(encodeSurfaceInteractionInstanceKey([left])).not.toBe(
        encodeSurfaceInteractionInstanceKey([right]),
      );
    }
  });

  it("never derives identity from display labels", () => {
    const key = encodeSurfaceInteractionInstanceKey(["plan", "doc-1"]);
    expect(key).not.toContain("Plan");
    expect(key).toBe('["plan","doc-1"]');
  });

  it("rejects non-encodable parts that would break injectivity", () => {
    const bad: unknown[] = [undefined, Number.NaN, Number.POSITIVE_INFINITY, {}, [], () => {}];
    for (const part of bad) {
      expect(() =>
        encodeSurfaceInteractionInstanceKey([part as SurfaceInteractionInstancePart]),
      ).toThrow(TypeError);
    }
  });

  it("rejects sparse part arrays instead of collapsing holes into explicit null", () => {
    const sparse = new Array(1) as unknown as SurfaceInteractionInstancePart[];
    expect(() => encodeSurfaceInteractionInstanceKey(sparse)).toThrow(TypeError);

    const sparseMiddle = ["plan", , "doc-1"] as unknown as SurfaceInteractionInstancePart[];
    expect(() => encodeSurfaceInteractionInstanceKey(sparseMiddle)).toThrow(TypeError);

    // Explicit null remains encodable and can no longer collide with a hole.
    expect(encodeSurfaceInteractionInstanceKey([null])).toBe("[null]");
  });

  it("ignores a custom toJSON on the caller-owned parts array", () => {
    const adversarial = ["plan"] as SurfaceInteractionInstancePart[] & {
      toJSON?: () => unknown;
    };
    adversarial.toJSON = () => ["other"];

    // The key is serialized from the validated values, not the decorated array.
    expect(encodeSurfaceInteractionInstanceKey(adversarial)).toBe('["plan"]');
    expect(encodeSurfaceInteractionInstanceKey(adversarial)).not.toBe(
      encodeSurfaceInteractionInstanceKey(["other"]),
    );
  });

  it("serializes the value read during validation when an accessor changes between reads", () => {
    let reads = 0;
    const adversarial = [] as SurfaceInteractionInstancePart[];
    Object.defineProperty(adversarial, "0", {
      get() {
        reads += 1;
        return reads === 1 ? "plan" : "other";
      },
      enumerable: true,
    });

    expect(encodeSurfaceInteractionInstanceKey(adversarial)).toBe('["plan"]');
    expect(reads).toBe(1);
  });
});

describe("buildSurfaceInteractionIdentity", () => {
  it("combines the exact surface ID with the encoded instance parts", () => {
    const identity = buildSurfaceInteractionIdentity({
      surfaceId: "plan",
      instanceParts: ["plan", "doc-1", 3],
    });
    expect(identity).toEqual({
      surfaceId: "plan",
      instanceKey: '["plan","doc-1",3]',
    });
  });

  it("carries no label or domain-specific fields", () => {
    const identity = buildSurfaceInteractionIdentity({
      surfaceId: "build",
      instanceParts: ["build", null],
    });
    expect(Object.keys(identity).sort()).toEqual(["instanceKey", "surfaceId"]);
  });
});

describe("sameSurfaceInteractionIdentity", () => {
  const identity = buildSurfaceInteractionIdentity({
    surfaceId: "plan",
    instanceParts: ["plan", "doc-1"],
  });

  it("returns false for null or undefined on either side", () => {
    expect(sameSurfaceInteractionIdentity(null, identity)).toBe(false);
    expect(sameSurfaceInteractionIdentity(identity, undefined)).toBe(false);
    expect(sameSurfaceInteractionIdentity(null, null)).toBe(false);
    expect(sameSurfaceInteractionIdentity(undefined, undefined)).toBe(false);
  });

  it("returns true only for exact surfaceId and instanceKey matches", () => {
    const same = buildSurfaceInteractionIdentity({
      surfaceId: "plan",
      instanceParts: ["plan", "doc-1"],
    });
    expect(sameSurfaceInteractionIdentity(identity, same)).toBe(true);

    expect(
      sameSurfaceInteractionIdentity(identity, { ...same, surfaceId: "build" }),
    ).toBe(false);
    expect(
      sameSurfaceInteractionIdentity(identity, {
        surfaceId: "plan",
        instanceKey: '["plan","doc-2"]',
      }),
    ).toBe(false);
  });

  it("ignores labels and other non-identity decoration", () => {
    const decorated = {
      ...identity,
      label: "Renamed surface",
    };
    expect(sameSurfaceInteractionIdentity(identity, decorated)).toBe(true);
  });
});
