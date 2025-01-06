import cx from "classnames";
import { JSX } from "solid-js";
import Icon, { IconVariant } from "../icon";

interface GroupProps {
  children: JSX.Element;
}

export const Group = (props: GroupProps) => (
  <div class="flex flex-col  gap-8 rounded-md border px-4 py-5 bg-def-2 border-def-2">
    {props.children}
  </div>
);

export type SectionVariant = "attention" | "danger";

interface SectionHeaderProps {
  variant: SectionVariant;
  headline: JSX.Element;
}
const variantColorsMap: Record<SectionVariant, string> = {
  attention: cx("bg-[#9BD8F2] fg-def-1"),
  danger: cx("bg-semantic-2 fg-semantic-2"),
};

const variantIconColorsMap: Record<SectionVariant, string> = {
  attention: cx("fg-def-1"),
  danger: cx("fg-semantic-3"),
};

const variantIconMap: Record<SectionVariant, IconVariant> = {
  attention: "Attention",
  danger: "Warning",
};

// SectionHeader component
export const SectionHeader = (props: SectionHeaderProps) => (
  <div
    class={cx(
      "flex items-center gap-3 rounded-md px-3 py-2",
      variantColorsMap[props.variant],
    )}
  >
    {
      <Icon
        icon={variantIconMap[props.variant]}
        class={cx("size-5", variantIconColorsMap[props.variant])}
      />
    }
    {props.headline}
  </div>
);

// Section component
interface SectionProps {
  children: JSX.Element;
}
export const Section = (props: SectionProps) => (
  <div class="flex flex-col gap-3">{props.children}</div>
);
