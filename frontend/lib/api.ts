export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api";

export async function api<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(
    `${API_URL}${path}`,
    {
      ...init,

      credentials: "include",

      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },

      cache: "no-store",
    }
  );

  if (!response.ok) {
    let message =
      `Request failed (${response.status})`;

    try {
      const body = await response.json();

      message =
        body.detail ??
        message;
    } catch {}

    throw new Error(message);
  }

  return response.json();
}
