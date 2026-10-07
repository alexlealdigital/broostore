import { useCallback, useState } from 'react';

/** Marca que a API esta demorando (servidor free acordando). Use `onSlow` nas chamadas e `reset` ao terminar. */
export function useSlowNotice() {
  const [slow, setSlow] = useState(false);
  const onSlow = useCallback(() => setSlow(true), []);
  const reset = useCallback(() => setSlow(false), []);
  return { slow, onSlow, reset };
}
