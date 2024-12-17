import { type JSX } from "solid-js";
import { Dynamic } from "solid-js/web";
import cx from "classnames";
import "./css/typography.css";

type Hierarchy = "body" | "title" | "headline" | "label";
type Color = "primary" | "secondary" | "tertiary";
type Weight = "normal" | "medium" | "bold";
type Tag = "span" | "p" | "h1" | "h2" | "h3" | "h4";

const colorMap: Record<Color, string> = {
  primary: cx("fnt-clr-primary"),
  secondary: cx("fnt-clr-secondary"),
  tertiary: cx("fnt-clr-tertiary"),
};

// type Size = "default" | "xs" | "s" | "m" | "l";
interface SizeForHierarchy {
  label: {
    default: string;
    xs: string;
    s: string;
  };
  body: {
    default: string;
    xs: string;
    s: string;
  };
  headline: {
    default: string;
    m: string;
    l: string;
  };
  title: {
    default: string;
    m: string;
    l: string;
  };
}

type AllowedSizes<H extends Hierarchy> = keyof SizeForHierarchy[H];

const sizeHierarchyMap: SizeForHierarchy = {
  body: {
    default: cx("fnt-body-default"),
    xs: cx("fnt-body-xs"),
    s: cx("fnt-body-s"),
    // m: cx("fnt-body-m"),
    // l: cx("fnt-body-l"),
  },
  headline: {
    default: cx("fnt-headline-default"),
    // xs: cx("fnt-headline-xs"),
    // s: cx("fnt-headline-s"),
    m: cx("fnt-headline-m"),
    l: cx("fnt-headline-l"),
  },
  title: {
    default: cx("fnt-title-default"),
    // xs: cx("fnt-title-xs"),
    // s: cx("fnt-title-s"),
    m: cx("fnt-title-m"),
    l: cx("fnt-title-l"),
  },
  label: {
    default: cx("fnt-label-default"),
    s: cx("fnt-label-s"),
    xs: cx("fnt-label-xs"),
  },
};

const weightMap: Record<Weight, string> = {
  normal: cx("fnt-weight-normal"),
  medium: cx("fnt-weight-medium"),
  bold: cx("fnt-weight-bold"),
};

interface TypographyProps<H extends Hierarchy> {
  hierarchy: H;
  size: AllowedSizes<H>;
  children: JSX.Element;
  weight?: Weight;
  color?: Color;
  inverted?: boolean;
  tag?: Tag;
  class?: string;
  classList?: Record<string, boolean>;
}
export const Typography = <H extends Hierarchy>(props: TypographyProps<H>) => {
  return (
    <Dynamic
      component={props.tag || "span"}
      class={cx(
        colorMap[props.color || "primary"],
        props.inverted && "fnt-clr--inverted",
        sizeHierarchyMap[props.hierarchy][props.size] as string,
        weightMap[props.weight || "normal"],
        props.class
      )}
      classList={props.classList}
    >
      {props.children}
    </Dynamic>
  );
};
