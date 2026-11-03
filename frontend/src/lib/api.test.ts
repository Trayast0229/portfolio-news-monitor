import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchArticle, searchTickers } from "./api";

describe("requests", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("give up with a message when the server never answers", async () => {
    vi.useFakeTimers();
    // A fetch that hangs until it is aborted, like a backend that is stuck.
    vi.stubGlobal("fetch", (_path: string, init?: RequestInit) =>
      new Promise((_resolve, reject) =>
        init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError"))),
      ),
    );
    let message: string | undefined;
    fetchArticle("https://news.example/bhp").catch((e: Error) => (message = e.message));

    await vi.advanceTimersByTimeAsync(10 * 60_000);

    expect(message).toMatch(/took too long/);
  });

  // Headers arrive at once but the body never finishes, until the request is aborted.
  function stubStalledBody() {
    vi.stubGlobal("fetch", (_path: string, init?: RequestInit) => {
      const body = new ReadableStream({
        start(c) {
          init?.signal?.addEventListener("abort", () => c.error(new DOMException("Aborted", "AbortError")));
        },
      });
      return Promise.resolve(new Response(body, { headers: { "content-type": "application/json" } }));
    });
  }

  it("give up with a message when the reply stalls halfway", async () => {
    vi.useFakeTimers();
    stubStalledBody();
    let message: string | undefined;
    fetchArticle("https://news.example/bhp").catch((e: Error) => (message = e.message));

    await vi.advanceTimersByTimeAsync(10 * 60_000);

    expect(message).toMatch(/took too long/);
  });

  it("stop reading a reply the caller cancelled", async () => {
    stubStalledBody();
    const ctrl = new AbortController();
    let settled = false;
    searchTickers("BHP", ctrl.signal).catch(() => (settled = true));
    await new Promise((r) => setTimeout(r, 0)); // let the headers arrive

    ctrl.abort();
    await new Promise((r) => setTimeout(r, 0));

    expect(settled).toBe(true);
  });

  it("don't run when the caller already cancelled them", async () => {
    // Like the browser's fetch: an already-aborted signal fails at once.
    vi.stubGlobal("fetch", (_path: string, init?: RequestInit) =>
      init?.signal?.aborted ? Promise.reject(new DOMException("Aborted", "AbortError")) : Promise.resolve(Response.json([])),
    );
    const cancelled = new AbortController();
    cancelled.abort();

    await expect(searchTickers("BHP", cancelled.signal)).rejects.toThrow();
  });
});
