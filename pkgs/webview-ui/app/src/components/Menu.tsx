import { children, createSignal, type JSX } from "solid-js";
import { useFloating } from "@/src/floating";
import {
  autoUpdate,
  flip,
  hide,
  offset,
  Placement,
  shift,
} from "@floating-ui/dom";
import cx from "classnames";
import { Button } from "./button";

interface MenuProps {
  /**
   * Used by the html API to associate the popover with the dispatcher button
   */
  popoverid: string;

  label: JSX.Element;

  children?: JSX.Element;
  buttonProps?: JSX.ButtonHTMLAttributes<HTMLButtonElement>;
  buttonClass?: string;
  /**
   * @default "bottom"
   */
  placement?: Placement;
}
export const Menu = (props: MenuProps) => {
  const c = children(() => props.children);
  const [reference, setReference] = createSignal<HTMLElement>();
  const [floating, setFloating] = createSignal<HTMLElement>();

  // `position` is a reactive object.
  const position = useFloating(reference, floating, {
    placement: "bottom",

    // pass options. Ensure the cleanup function is returned.
    whileElementsMounted: (reference, floating, update) =>
      autoUpdate(reference, floating, update, {
        animationFrame: true,
      }),
    middleware: [
      offset(5),
      shift(),
      flip(),

      hide({
        strategy: "referenceHidden",
      }),
    ],
  });

  return (
    <div>
      <Button
        variant="light"
        popovertarget={props.popoverid}
        popovertargetaction="toggle"
        ref={setReference}
        class={cx(
          "btn btn-ghost btn-outline join-item btn-sm",
          props.buttonClass,
        )}
        {...props.buttonProps}
      >
        {props.label}
      </Button>
      <div
        popover="auto"
        id={props.popoverid}
        ref={setFloating}
        style={{
          margin: 0,
          position: position.strategy,
          top: `${position.y ?? 0}px`,
          left: `${position.x ?? 0}px`,
        }}
        class="bg-transparent"
      >
        {c()}
      </div>
    </div>
  );
};
