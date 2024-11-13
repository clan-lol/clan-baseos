import type { JSX } from "solid-js";
interface LabelProps {
  label: JSX.Element;
  required?: boolean;
}
export const Label = (props: LabelProps) => (
  <span
    class="label-text block"
    classList={{
      "after:ml-0.5 after:text-primary after:content-['*']": props.required,
    }}
  >
    {props.label}
  </span>
);
