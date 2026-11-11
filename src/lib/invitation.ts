/** The invitation token from a deep link (`?token=`), or from the whole emailed link pasted by hand. */
export function tokenFrom(text: string): string {
  const found = /[?&]token=([^&\s]+)/.exec(text);
  return decodeURIComponent(found ? found[1] : text.trim());
}
