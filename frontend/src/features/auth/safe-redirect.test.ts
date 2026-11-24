import { isSafeRedirect } from "./safe-redirect";

describe("isSafeRedirect", () => {
  it.each(["/", "/words?page=2", "/a/b#c"])("aceita caminho interno %s", (path) => {
    expect(isSafeRedirect(path)).toBe(true);
  });

  it.each(["https://evil.example", "//evil.example", "/\\evil.example", "words", ""])(
    "recusa %s",
    (path) => {
      expect(isSafeRedirect(path)).toBe(false);
    },
  );
});
