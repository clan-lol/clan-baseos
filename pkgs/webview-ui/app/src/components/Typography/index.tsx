import { type JSX } from "solid-js";
import { Dynamic } from "solid-js/web";
import cx from "classnames";
import "./css/typography.css";

type Hierarchy = "body" | "title" | "headline";
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
};

const weightMap: Record<Weight, string> = {
  normal: cx("fnt-weight-normal"),
  medium: cx("fnt-weight-medium"),
  bold: cx("fnt-weight-bold"),
};

interface TypographyProps<H extends Hierarchy> {
  hierarchy: H;
  weight?: Weight;
  color?: Color;
  inverted?: boolean;
  size: AllowedSizes<H>;
  tag?: Tag;
  children: JSX.Element;
  classes?: string;
}
export const Typography = <H extends Hierarchy>(props: TypographyProps<H>) => {
  const {
    size,
    color = "primary",
    inverted,
    hierarchy,
    weight = "normal",
    tag,
    children,
    classes,
  } = props;

  return (
    <Dynamic
      component={tag}
      class={cx(
        classes,
        colorMap[color],
        inverted && "fnt-clr--inverted",
        sizeHierarchyMap[hierarchy][size] as string,
        weightMap[weight],
      )}
    >
      {children}
    </Dynamic>
  );
};
