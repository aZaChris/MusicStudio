// How a person is shown in the portal. The email is only the fallback: an account created
// by an invitation can have empty name fields.
type Named = { first_name: string; last_name: string; email: string }

export const firstName = (u: Named) => u.first_name.trim() || u.email.split('@')[0]

export const fullName = (u: Named) => `${u.first_name} ${u.last_name}`.trim() || u.email
