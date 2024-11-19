import { createEffect, Show, type JSX } from "solid-js";
import cx from "classnames";
import { Label } from "../base/label";

interface TextInputProps {
  value: string;
  inputProps?: JSX.InputHTMLAttributes<HTMLInputElement>;
  label: JSX.Element;
  altLabel?: JSX.Element;
  helperText?: JSX.Element;
  error?: string;
  required?: boolean;
  type?: string;
  inlineLabel?: JSX.Element;
  class?: string;
  adornment?: {
    position: "start" | "end";
    content: JSX.Element;
  };
  disabled?: boolean;
  placeholder?: string;
}

export function TextInput(props: TextInputProps) {
  const value = () => props.value;

  return (
    <label
      class={cx("form-control w-full", props.class)}
      aria-disabled={props.disabled}
    >
      <div class="label">
        <Label label={props.label} required={props.required} />
        <span class="label-text-alt block">{props.altLabel}</span>
      </div>

      <div class="input input-bordered flex items-center gap-2">
        <Show when={props.adornment && props.adornment.position === "start"}>
          {props.adornment?.content}
        </Show>
        {props.inlineLabel}
        <input
          {...props.inputProps}
          value={value()}
          type={props.type ? props.type : "text"}
          class="grow"
          classList={{
            "input-disabled": props.disabled,
          }}
          placeholder={`${props.placeholder || props.label}`}
          required
          disabled={props.disabled}
        />
        <Show when={props.adornment && props.adornment.position === "end"}>
          {props.adornment?.content}
        </Show>
      </div>
      <div class="label">
        {props.helperText && (
          <span class="label-text text-neutral">{props.helperText}</span>
        )}
        {props.error && (
          <span class="label-text-alt font-bold text-error-700">
            {props.error}
          </span>
        )}
      </div>
    </label>
  );
}
