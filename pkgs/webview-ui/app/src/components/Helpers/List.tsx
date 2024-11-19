import { type JSX } from "solid-js";

type sizes = "small" | "medium" | "large";

const gapSizes: { [size in sizes]: string } = {
  small: "gap-2",
  medium: "gap-4",
  large: "gap-6",
};

interface List {
  children: JSX.Element;
  gapSize: sizes;
}

export const List = (props: List) => {
  const { children, gapSize } = props;

  return <ul class={`flex flex-col ${gapSizes[gapSize]}`}> {children}</ul>;
};
