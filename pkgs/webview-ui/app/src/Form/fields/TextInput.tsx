import { splitProps, type JSX } from "solid-js";
import { InputBase, InputError, InputLabel } from "@/src/components/inputBase";
import { Typography } from "@/src/components/Typography";
import { FieldLayout } from "./layout";

interface TextInputProps {
  // Common
  error?: string;
  required?: boolean;
  disabled?: boolean;
  // Passed to input
  value: string;
  inputProps?: JSX.InputHTMLAttributes<HTMLInputElement>;
  placeholder?: string;
  // Passed to label
  label: JSX.Element;
  help?: string;
  // Passed to layouad
  class?: string;
}

export function TextInput(props: TextInputProps) {
  const [layoutProps, rest] = splitProps(props, ["class"]);
  return (
    <FieldLayout
      label={
        <InputLabel
          class="col-span-2"
          required={props.required}
          error={!!props.error}
          help={props.help}
        >
          {props.label}
        </InputLabel>
      }
      field={
        <InputBase
          error={!!props.error}
          required={props.required}
          disabled={props.disabled}
          placeholder={props.placeholder}
          class="col-span-10"
          {...props.inputProps}
          value={props.value}
        />
      }
      error={props.error && <InputError error={props.error} />}
      {...layoutProps}
    />
  );
}
