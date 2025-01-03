import { JSX, splitProps } from "solid-js";
import cx from "classnames";

interface LayoutProps extends JSX.HTMLAttributes<HTMLDivElement> {
  field?: JSX.Element;
  label?: JSX.Element;
  error?: JSX.Element;
}
export const FieldLayout = (props: LayoutProps) => {
  const [intern, divProps] = splitProps(props, [
    "field",
    "label",
    "error",
    "class",
  ]);
  return (
    <div
      class={cx("grid grid-cols-10 items-center", intern.class)}
      {...divProps}
    >
      <label class="col-span-5">{props.label}</label>
      <div class="col-span-5">{props.field}</div>
      {props.error && <span class="col-span-full">{props.error}</span>}
    </div>
  );
};
