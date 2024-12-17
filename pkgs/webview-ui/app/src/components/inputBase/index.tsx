import cx from "classnames";
import { createEffect, JSX, splitProps } from "solid-js";
import Icon, { IconVariant } from "../icon";
import { Typography } from "../Typography";

type Variants = "outlined" | "ghost";
interface InputBaseProps {
  variant?: Variants;
  value?: string;
  inputProps?: JSX.InputHTMLAttributes<HTMLInputElement>;
  required?: boolean;
  type?: string;
  inlineLabel?: JSX.Element;
  class?: string;
  placeholder?: string;
  disabled?: boolean;
  readonly?: boolean;
  error?: boolean;
  icon?: IconVariant;
}

const variantBorder: Record<Variants, string> = {
  outlined: "border border-inv-3",
  ghost: "",
};

const fgStateClasses = cx("aria-disabled:fg-def-4 aria-readonly:fg-def-3");

export const InputBase = (props: InputBaseProps) => {
  const [, inputProps] = splitProps(props, ["class"]);

  createEffect(() => {
    console.log("InputBase", props.value, props.variant);
  });
  return (
    <div
      class={cx(
        // Layout
        "flex px-2 py-[0.375rem] flex-shrink-0 items-center justify-center gap-2 text-sm leading-6",

        // Background
        "bg-def-1 hover:bg-acc-1",

        // Text
        "fg-def-1",
        fgStateClasses,
        // Border
        variantBorder[props.variant || "outlined"],
        "rounded-sm",
        "hover:border-inv-4",
        "aria-disabled:border-def-2 aria-disabled:border",
        // Outline
        "outline-offset-1 outline-1",
        "active:outline active:outline-inv-3",
        "focus-visible:outline-double  focus-visible:outline-int-1",

        // Cursor
        "aria-readonly:cursor-no-drop",
        props.class,
      )}
      classList={{
        [cx("!border !border-semantic-1 !outline-semantic-1")]: !!props.error,
      }}
      aria-invalid={props.error}
      aria-disabled={props.disabled}
      aria-readonly={props.readonly}
      tabIndex={0}
      role="textbox"
    >
      {props.icon && (
        <i
          class={cx("inline-flex fg-def-2", fgStateClasses)}
          aria-invalid={props.error}
          aria-disabled={props.disabled}
          aria-readonly={props.readonly}
        >
          <Icon icon={props.icon} font-size="inherit" color="inherit" />
        </i>
      )}
      <input
        tabIndex={-1}
        class="w-full bg-transparent outline-none aria-readonly:cursor-no-drop"
        value={props.value}
        type={props.type ? props.type : "text"}
        readOnly={props.readonly}
        placeholder={`${props.placeholder || ""}`}
        required={props.required}
        disabled={props.disabled}
        aria-invalid={props.error}
        aria-disabled={props.disabled}
        aria-readonly={props.readonly}
        {...inputProps}
      />
    </div>
  );
};

interface InputLabelProps extends JSX.LabelHTMLAttributes<HTMLLabelElement> {
  description?: string;
  required?: boolean;
  error?: boolean;
  help?: string;
}
export const InputLabel = (props: InputLabelProps) => {
  const [labelProps, forwardProps] = splitProps(props, ["class"]);
  return (
    <label
      class={cx("flex items-center gap-1", labelProps.class)}
      {...forwardProps}
    >
      <Typography
        hierarchy="label"
        size="default"
        weight="bold"
        class="!fg-def-1"
        classList={{
          [cx("!fg-semantic-1")]: !!props.error,
        }}
        aria-invalid={props.error}
      >
        {props.children}
        {props.required && (
          <span class="inline-flex px-1 align-bottom leading-[0.5] fg-def-3">
            {"*"}
          </span>
        )}
        {props.help && (
          <span
            class="tooltip tooltip-bottom inline px-2"
            data-tip={props.help}
            style={{
              "--tooltip-color": "#EFFFFF",
              "--tooltip-text-color": "#0D1416",
              "--tooltip-tail": "0.8125rem",
            }}
          >
            <Icon class="inline fg-def-3" icon={"Info"} width={"0.8125rem"} />
          </span>
        )}
      </Typography>
      <Typography hierarchy="body" size="xs" weight="normal" color="secondary">
        {props.description}
      </Typography>
    </label>
  );
};
