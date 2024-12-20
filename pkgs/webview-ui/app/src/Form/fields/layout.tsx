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
      class={cx("grid grid-cols-12 items-center", intern.class)}
      classList={{
        "mb-[14.5px]": !props.error,
      }}
      {...divProps}
    >
      <label class="col-span-2">{props.label}</label>
      <div class="col-span-10">{props.field}</div>
      {props.error && <span class="col-span-full">{props.error}</span>}
    </div>
  );
};
