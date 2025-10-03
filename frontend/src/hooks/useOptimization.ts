/**
 * Performance optimization utilities and hooks
 * Provides tools for optimizing React component performance
 */

import { useRef, useEffect, useState } from 'react';
import type { DependencyList } from 'react';

/**
 * Hook that returns a stable callback reference
 * Prevents unnecessary re-renders when passing callbacks to child components
 * 
 * @example
 * const handleClick = useStableCallback(() => {
 *   console.log('Clicked with state:', someState);
 * }, [someState]);
 */
export function useStableCallback<T extends (...args: any[]) => any>(
  callback: T,
  deps: DependencyList
): T {
  const callbackRef = useRef<T>(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, deps);

  const stableCallback = useRef(
    (...args: Parameters<T>) => callbackRef.current(...args)
  ).current;

  return stableCallback as T;
}

/**
 * Hook for debouncing a value
 * Useful for search inputs and expensive operations
 * 
 * @example
 * const debouncedSearchTerm = useDebounce(searchTerm, 500);
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Hook for throttling a callback
 * Limits the rate at which a function can fire
 * 
 * @example
 * const handleScroll = useThrottle(() => {
 *   console.log('Scrolled!');
 * }, 200);
 */
export function useThrottle<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): T {
  const lastRun = useRef(Date.now());
  const timeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);

  const throttledCallback = useRef((...args: Parameters<T>) => {
    const now = Date.now();
    const timeSinceLastRun = now - lastRun.current;

    if (timeSinceLastRun >= delay) {
      callback(...args);
      lastRun.current = now;
    } else {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(() => {
        callback(...args);
        lastRun.current = Date.now();
      }, delay - timeSinceLastRun);
    }
  }).current;

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return throttledCallback as T;
}

/**
 * Hook that tracks previous value
 * Useful for comparing current value with previous
 * 
 * @example
 * const prevCount = usePrevious(count);
 * if (prevCount !== count) {
 *   console.log('Count changed from', prevCount, 'to', count);
 * }
 */
export function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T | undefined>(undefined);

  useEffect(() => {
    ref.current = value;
  }, [value]);

  return ref.current;
}

/**
 * Deep equality check for objects and arrays
 */
function deepEqual(a: any, b: any): boolean {
  if (a === b) return true;
  if (a == null || b == null) return false;
  if (typeof a !== typeof b) return false;

  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false;
    return a.every((val, index) => deepEqual(val, b[index]));
  }

  if (typeof a === 'object' && typeof b === 'object') {
    const keysA = Object.keys(a);
    const keysB = Object.keys(b);
    if (keysA.length !== keysB.length) return false;
    return keysA.every(key => deepEqual(a[key], b[key]));
  }

  return false;
}

/**
 * Hook that only updates if value deeply changed
 * Useful for memoizing objects and arrays
 * 
 * @example
 * const sortedData = useDeepMemo(
 *   () => data.sort((a, b) => a.value - b.value),
 *   [data]
 * );
 */
export function useDeepMemo<T>(factory: () => T, deps: DependencyList): T {
  const ref = useRef<{ deps: DependencyList; value: T } | undefined>(undefined);

  if (!ref.current || !deepEqual(ref.current.deps, deps)) {
    ref.current = {
      deps,
      value: factory(),
    };
  }

  return ref.current.value;
}

/**
 * Hook for measuring render performance
 * Only active in development mode
 * 
 * @example
 * useRenderCount('MyComponent');
 */
export function useRenderCount(componentName: string) {
  const renderCount = useRef(0);

  useEffect(() => {
    renderCount.current += 1;
    if (process.env.NODE_ENV === 'development') {
      console.log(`[Perf] ${componentName} rendered ${renderCount.current} times`);
    }
  });

  return renderCount.current;
}

/**
 * Hook for lazy initialization of expensive computations
 * Only runs once on mount
 * 
 * @example
 * const heavyData = useLazyInit(() => processLargeDataset(rawData));
 */
export function useLazyInit<T>(init: () => T): T {
  const ref = useRef<{ value: T } | undefined>(undefined);

  if (!ref.current) {
    ref.current = { value: init() };
  }

  return ref.current.value;
}

/**
 * Hook for batching multiple state updates
 * Reduces number of re-renders
 * 
 * @example
 * const [batchedState, setBatchedState] = useBatchedState({ count: 0, name: '' });
 * setBatchedState({ count: 1 }); // Only triggers one re-render
 * setBatchedState({ name: 'John' }); // Batched with previous update
 */
export function useBatchedState<T extends Record<string, any>>(
  initialState: T
): [T, (updates: Partial<T>) => void] {
  const [state, setState] = useState<T>(initialState);
  const updatesRef = useRef<Partial<T>>({});
  const rafRef = useRef<number | undefined>(undefined);

  const setBatchedState = useStableCallback((updates: Partial<T>) => {
    Object.assign(updatesRef.current, updates);

    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
    }

    rafRef.current = requestAnimationFrame(() => {
      setState(prev => ({ ...prev, ...updatesRef.current }));
      updatesRef.current = {};
    });
  }, []);

  useEffect(() => {
    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, []);

  return [state, setBatchedState];
}

/**
 * Hook for intersection observer
 * Useful for lazy loading and infinite scroll
 * 
 * @example
 * const [ref, isVisible] = useIntersectionObserver();
 * return <div ref={ref}>{isVisible && <ExpensiveComponent />}</div>;
 */
export function useIntersectionObserver(
  options: IntersectionObserverInit = {}
): [React.RefCallback<Element>, boolean] {
  const [isVisible, setIsVisible] = useState(false);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const elementRef = useRef<Element | null>(null);

  const refCallback = useStableCallback((node: Element | null) => {
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    if (node) {
      observerRef.current = new IntersectionObserver(([entry]) => {
        setIsVisible(entry.isIntersecting);
      }, options);

      observerRef.current.observe(node);
      elementRef.current = node;
    }
  }, [options.threshold, options.rootMargin]);

  useEffect(() => {
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, []);

  return [refCallback, isVisible];
}
