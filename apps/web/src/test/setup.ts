import '@testing-library/jest-dom/vitest';

// jsdom nao implementa scrollIntoView
if (typeof Element !== 'undefined' && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => undefined;
}
// ...nem scrollTo
if (typeof window !== 'undefined') {
  window.scrollTo = (() => undefined) as typeof window.scrollTo;
}
