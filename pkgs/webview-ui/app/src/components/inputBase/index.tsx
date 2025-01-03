import cx from "classnames";
import { JSX, Ref, Show, splitProps } from "solid-js";
import Icon, { IconVariant } from "../icon";
import { Typography, TypographyProps } from "../Typography";

export type InputVariant = "outlined" | "ghost";
interface InputBaseProps {
  variant?: InputVariant;
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
  /** Overrides the input element */
  inputElem?: JSX.Element;
  divRef?: Ref<HTMLDivElement>;
}

const variantBorder: Record<InputVariant, string> = {
  outlined: "border border-inv-3",
  ghost: "",
};

const fgStateClasses = cx("aria-disabled:fg-def-4 aria-readonly:fg-def-3");

export const InputBase = (props: InputBaseProps) => {
  const [internal, inputProps] = splitProps(props, ["class", "divRef"]);
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
      ref={internal.divRef}
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
      <Show when={!props.inputElem} fallback={props.inputElem}>
        <input
          tabIndex={-1}
          class="w-full bg-transparent outline-none"
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
      </Show>
    </div>
  );
};

export interface InputLabelProps
  extends JSX.LabelHTMLAttributes<HTMLLabelElement> {
  description?: string;
  required?: boolean;
  error?: boolean;
  help?: string;
  labelAction?: JSX.Element;
}
export const InputLabel = (props: InputLabelProps) => {
  const [labelProps, forwardProps] = splitProps(props, [
    "class",
    "labelAction",
  ]);
  return (
    <label
      class={cx("flex items-center gap-1", labelProps.class)}
      {...forwardProps}
    >
      <span class="flex flex-col justify-center">
        <span>
          <Typography
            hierarchy="label"
            size="default"
            weight="bold"
            class="inline-flex gap-1 align-middle !fg-def-1"
            classList={{
              [cx("!fg-semantic-1")]: !!props.error,
            }}
            aria-invalid={props.error}
          >
            {props.children}
          </Typography>
          {props.required && (
            <Typography
              class="inline-flex px-1 align-text-top leading-[0.5] fg-def-4"
              useExternColor={true}
              hierarchy="label"
              weight="bold"
              size="xs"
            >
              {"∗"}
            </Typography>
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
        </span>
        <Typography
          hierarchy="body"
          size="xs"
          weight="normal"
          color="secondary"
        >
          {props.description}
        </Typography>
      </span>
      {props.labelAction}
    </label>
  );
};

interface InputErrorProps {
  error: string;
  typographyProps?: TypographyProps;
}
export const InputError = (props: InputErrorProps) => {
  const [typoClasses, rest] = splitProps(
    props.typographyProps || { class: "" },
    ["class"],
  );
  return (
    <Typography
      hierarchy="body"
      // @ts-expect-error: Dependent type is to complex to check how it is coupled to the override for now
      size="xxs"
      weight="medium"
      class={cx("col-span-full px-1 !fg-semantic-4", typoClasses)}
      {...rest}
    >
      {props.error}
    </Typography>
  );
};
