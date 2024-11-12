import { createEffect, createMemo, createSignal, onCleanup } from "solid-js";
import type {
  ComputePositionConfig,
  ComputePositionReturn,
  ReferenceElement,
} from "@floating-ui/dom";
import { computePosition } from "@floating-ui/dom";

export interface UseFloatingOptions<
  R extends ReferenceElement,
  F extends HTMLElement,
> extends Partial<ComputePositionConfig> {
  whileElementsMounted?: (
    reference: R,
    floating: F,
    update: () => void,
  ) => // eslint-disable-next-line @typescript-eslint/no-invalid-void-type
  void | (() => void);
}

interface UseFloatingState extends Omit<ComputePositionReturn, "x" | "y"> {
  x?: number | null;
  y?: number | null;
}

export interface UseFloatingResult extends UseFloatingState {
  update(): void;
}

export function useFloating<R extends ReferenceElement, F extends HTMLElement>(
  reference: () => R | undefined | null,
  floating: () => F | undefined | null,
  options?: UseFloatingOptions<R, F>,
): UseFloatingResult {
  const placement = () => options?.placement ?? "bottom";
  const strategy = () => options?.strategy ?? "absolute";

  const [data, setData] = createSignal<UseFloatingState>({
    x: null,
    y: null,
    placement: placement(),
    strategy: strategy(),
    middlewareData: {},
  });

  const [error, setError] = createSignal<{ value: unknown } | undefined>();

  createEffect(() => {
    const currentError = error();
    if (currentError) {
      throw currentError.value;
    }
  });

  const version = createMemo(() => {
    reference();
    floating();
    return {};
  });

  function update() {
    const currentReference = reference();
    const currentFloating = floating();

    if (currentReference && currentFloating) {
      const capturedVersion = version();
      computePosition(currentReference, currentFloating, {
        middleware: options?.middleware,
        placement: placement(),
        strategy: strategy(),
      }).then(
        (currentData) => {
          // Check if it's still valid
          if (capturedVersion === version()) {
            setData(currentData);
          }
        },
        (err) => {
          setError(err);
        },
      );
    }
  }

  createEffect(() => {
    const currentReference = reference();
    const currentFloating = floating();

    options?.middleware;
    placement();
    strategy();

    if (currentReference && currentFloating) {
      if (options?.whileElementsMounted) {
        const cleanup = options.whileElementsMounted(
          currentReference,
          currentFloating,
          update,
        );

        if (cleanup) {
          onCleanup(cleanup);
        }
      } else {
        update();
      }
    }
  });

  return {
    get x() {
      return data().x;
    },
    get y() {
      return data().y;
    },
    get placement() {
      return data().placement;
    },
    get strategy() {
      return data().strategy;
    },
    get middlewareData() {
      return data().middlewareData;
    },
    update,
  };
}
