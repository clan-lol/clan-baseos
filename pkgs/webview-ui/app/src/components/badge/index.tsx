import { JSX } from "solid-js";
import cx from "classnames";
import Icon, { IconVariant } from "../icon";
import { Typography } from "../Typography";

interface BadgeProps {
  color: keyof typeof colorMap;
  children: JSX.Element;
  icon?: IconVariant;
  class?: string;
}

const colorMap = {
  primary: cx("bg-primary-800 text-primary-100"),
  secondary: cx("bg-secondary-800 text-secondary-100"),
  blue: "bg-blue-100 text-blue-800",
  gray: "bg-gray-100 text-gray-800",
  green: "bg-green-100 text-green-800",
  orange: "bg-orange-100 text-orange-800",
  red: "bg-red-100 text-red-800",
  yellow: "bg-yellow-100 text-yellow-800",
};

export const Badge = (props: BadgeProps) => {
  return (
    <div
      class={cx(
        "flex px-4 py-2 rounded-sm justify-center items-center gap-1",
        colorMap[props.color],
        props.class,
      )}
    >
      {props.icon && <Icon icon={props.icon} class="size-4" />}
      <Typography hierarchy="label" size="default" color="inherit">
        {props.children}
      </Typography>
    </div>
  );
};
