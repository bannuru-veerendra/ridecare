/**
 * Global TypeScript types shared across features.
 * Feature-specific types live inside their own feature folder.
 */

/**
 * Cursor-based paginated response from the API.
 * Pass next_cursor as ?cursor= in the next request.
 */
export interface CursorPage<T> {
    items: T[];
    next_cursor: string | null;
    has_more: boolean;
    total: number;
}

/** Shared user shape from /auth/register and /users/me. */
export interface User {
    id: string;
    email: string;
    full_name: string;
    email_verified: boolean;
    email_service_reminders: boolean;
    email_document_reminders: boolean;
}
