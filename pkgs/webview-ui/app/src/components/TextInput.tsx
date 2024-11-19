import { FieldValues, FormStore, ResponseData } from "@modular-forms/solid";
import { Show, type JSX } from "solid-js";
import cx from "classnames";

interface TextInputProps<T extends FieldValues, R extends ResponseData> {
  formStore: FormStore<T, R>;
  value: string;
  inputProps: JSX.InputHTMLAttributes<HTMLInputElement>;
  label: JSX.Element;
  error?: string;
  required?: boolean;
  type?: string;
  inlineLabel?: JSX.Element;
  class?: string;
  adornment?: {
    position: "start" | "end";
    content: JSX.Element;
  };
  placeholder?: string;
}

export function TextInput<T extends FieldValues, R extends ResponseData>(
  props: TextInputProps<T, R>,
) {
  const value = () => props.value;

  return (
    <label
      class={cx("form-control w-full", props.class)}
      aria-disabled={props.formStore.submitting}
    >
      <div class="label">
        <span
          class="label-text block"
          classList={{
            "after:ml-0.5 after:text-primary after:content-['*']":
              props.required,
          }}
        >
          {props.label}
        </span>
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
            "input-disabled": props.formStore.submitting,
          }}
          placeholder={`${props.placeholder || props.label}`}
          required
          disabled={props.formStore.submitting}
        />
        <Show when={props.adornment && props.adornment.position === "end"}>
          {props.adornment?.content}
        </Show>
      </div>
      {props.error && (
        <span class="label-text-alt font-bold text-error-700">
          {props.error}
        </span>
      )}
    </label>
  );
}
