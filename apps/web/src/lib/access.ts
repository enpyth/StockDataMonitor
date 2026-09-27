const allowedUserEmailValue = String(import.meta.env.VITE_ALLOWED_USER_EMAILS ?? '')

const allowedUserEmails = allowedUserEmailValue
  .split(',')
  .map((email: string) => email.trim().toLowerCase())
  .filter(Boolean)

export function isAllowedUserEmail(email: string | null | undefined) {
  if (allowedUserEmails.length === 0) return true
  return Boolean(email && allowedUserEmails.includes(email.trim().toLowerCase()))
}
