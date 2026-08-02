import { afterEach, describe, expect, it, vi } from "vitest";

import { apiBinary, apiBoundedJson, APIError } from "@/lib/api";
import {
  downloadTransient,
  PASSPORT_MEDIA_TYPE,
  safePassportFilename,
  safePassportMessage,
} from "@/lib/passport";

describe("passport download safeguards", () => {
  afterEach(() => vi.restoreAllMocks());

  it("uses only a validated UUID-derived filename", () => {
    expect(safePassportFilename("urn:uuid:00000000-0000-0000-0000-000000000042")).toBe(
      "answer-passport-00000000-0000-0000-0000-000000000042.zip",
    );
    for (const unsafe of [
      "../passport.zip",
      "/absolute/passport.zip",
      "..\\passport.zip",
      "urn:uuid:x\r\nContent-Disposition: unsafe",
      'urn:uuid:<script>alert("x")</script>',
      `urn:uuid:${"a".repeat(4096)}`,
      "urn:uuid:\u202epiz.troppussap",
    ]) {
      expect(() => safePassportFilename(unsafe)).toThrow();
    }
  });

  it("rejects wrong content type and oversized binary responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("bad", { status: 200, headers: { "Content-Type": "text/html" } }),
      ),
    );
    await expect(apiBinary("/download", PASSPORT_MEDIA_TYPE, 100)).rejects.toThrow(
      "download format is invalid",
    );

    vi.mocked(fetch).mockResolvedValue(
      new Response("large", {
        status: 200,
        headers: { "Content-Type": PASSPORT_MEDIA_TYPE, "Content-Length": "101" },
      }),
    );
    await expect(apiBinary("/download", PASSPORT_MEDIA_TYPE, 100)).rejects.toThrow(
      "exceeds the safety limit",
    );
  });

  it("cancels a chunked response as soon as the streaming limit is exceeded", async () => {
    const cancel = vi.fn();
    const reader = {
      read: vi
        .fn()
        .mockResolvedValueOnce({ done: false, value: new Uint8Array(60) })
        .mockResolvedValueOnce({ done: false, value: new Uint8Array(60) }),
      cancel,
      releaseLock: vi.fn(),
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ "Content-Type": PASSPORT_MEDIA_TYPE }),
        body: { getReader: () => reader },
      }),
    );

    await expect(apiBinary("/download", PASSPORT_MEDIA_TYPE, 100)).rejects.toThrow(
      "exceeds the safety limit",
    );
    expect(cancel).toHaveBeenCalledOnce();
  });

  it("requires JSON media type for bounded public trust material", async () => {
    const cancel = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ "Content-Type": "text/html" }),
        body: { cancel },
      }),
    );

    await expect(apiBoundedJson("/trust", 100)).rejects.toThrow("download format is invalid");
    expect(cancel).toHaveBeenCalledOnce();
  });

  it("never renders a server-crafted error as a trusted client download error", () => {
    expect(safePassportMessage(new APIError(500, "The download leaked /storage/path"))).toBe(
      "The passport service is unavailable.",
    );
  });

  it("revokes the transient object URL after one download task", () => {
    vi.useFakeTimers();
    const createObjectURL = vi.fn(() => "blob:safe");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const click = vi.fn();
    const remove = vi.fn();
    vi.spyOn(document, "createElement").mockReturnValue({ click, remove } as unknown as HTMLAnchorElement);
    vi.spyOn(document.body, "appendChild").mockImplementation((node) => node);

    const cleanup = downloadTransient(new Blob(["opaque"]), "answer-passport-safe.zip");
    expect(click).toHaveBeenCalledOnce();
    expect(remove).toHaveBeenCalledOnce();
    expect(revokeObjectURL).not.toHaveBeenCalled();
    vi.runAllTimers();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:safe");
    cleanup();
    expect(revokeObjectURL).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });
});
