import { afterEach, describe, expect, it, vi } from "vitest";

import { apiBinary } from "@/lib/api";
import {
  downloadTransient,
  PASSPORT_MEDIA_TYPE,
  safePassportFilename,
} from "@/lib/passport";

describe("passport download safeguards", () => {
  afterEach(() => vi.restoreAllMocks());

  it("uses only a validated UUID-derived filename", () => {
    expect(safePassportFilename("urn:uuid:00000000-0000-0000-0000-000000000042")).toBe(
      "answer-passport-00000000-0000-0000-0000-000000000042.zip",
    );
    expect(() => safePassportFilename("urn:uuid:x\r\nContent-Disposition: unsafe")).toThrow();
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

  it("revokes the transient object URL after one download task", () => {
    vi.useFakeTimers();
    const createObjectURL = vi.fn(() => "blob:safe");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const click = vi.fn();
    const remove = vi.fn();
    vi.spyOn(document, "createElement").mockReturnValue({ click, remove } as unknown as HTMLAnchorElement);
    vi.spyOn(document.body, "appendChild").mockImplementation((node) => node);

    downloadTransient(new Blob(["opaque"]), "answer-passport-safe.zip");
    expect(click).toHaveBeenCalledOnce();
    expect(remove).toHaveBeenCalledOnce();
    expect(revokeObjectURL).not.toHaveBeenCalled();
    vi.runAllTimers();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:safe");
    vi.useRealTimers();
  });
});
