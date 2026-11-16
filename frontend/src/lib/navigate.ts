/**
 * Leave the app for an external page (Stripe's hosted onboarding and payment pages).
 * A function of its own so tests can replace it: jsdom cannot navigate.
 */
export function goToExternal(url: string): void {
  window.location.assign(url)
}
