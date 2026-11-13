/**
 * Aceita só caminhos internos ("/algo"). Recusa "//host" e "/\host", que o
 * navegador interpreta como outra origem (open redirect).
 */
export function isSafeRedirect(path: string): boolean {
  return path.startsWith("/") && !path.startsWith("//") && !path.startsWith("/\\");
}
