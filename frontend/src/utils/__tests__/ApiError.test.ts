import { describe, it, expect } from "vitest";
import { ApiError } from "../errors";

describe("ApiError", () => {
  it("stores statusCode and code", () => {
    const err = new ApiError(404, { message: "Not found", code: "not_found" });
    expect(err.statusCode).toBe(404);
    expect(err.code).toBe("not_found");
    expect(err.message).toBe("Not found");
    expect(err.name).toBe("ApiError");
  });

  it("stores details when provided", () => {
    const err = new ApiError(422, { message: "Invalid", code: "validation_error", details: { field: "email" } });
    expect(err.details).toEqual({ field: "email" });
  });

  it("has correct prototype chain", () => {
    const err = new ApiError(500, { message: "Server error", code: "internal" });
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toBeInstanceOf(Error);
  });
});
