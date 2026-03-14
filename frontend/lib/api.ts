/**
 * Client API pour communiquer avec le backend Python FastAPI.
 * Toutes les requêtes passent par le proxy Next.js (/api/python/ → :8765/api/).
 */

const API_BASE = "/api/python";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function fetchAPI<T = unknown>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new ApiError(res.status, `API error: ${res.status}`);
  }
  return res.json();
}

export async function mutateAPI<T = unknown>(
  path: string,
  method: "POST" | "PATCH" | "DELETE",
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      // Token sera ajouté si configuré
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    throw new ApiError(res.status, `API error: ${res.status}`);
  }
  return res.json();
}
