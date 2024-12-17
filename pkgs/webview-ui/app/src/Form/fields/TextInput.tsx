import { createEffect, Show, type JSX } from "solid-js";
import cx from "classnames";
import { Label } from "../base/label";
import { InputBase, InputLabel } from "@/src/components/inputBase";
import { Typography } from "@/src/components/Typography";

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
  // createEffect(() => {
  //   console.log("TextInput", props.error, props.value);
  // });
  return (
    <div
      class="grid grid-cols-12"
      classList={{
        "mb-[14.5px]": !props.error,
      }}
    >
      <InputLabel
        class="col-span-2"
        required={props.required}
        error={!!props.error}
      >
        {props.label}
      </InputLabel>
      <InputBase
        error={!!props.error}
        class="col-span-10"
        {...props.inputProps}
        value={props.value}
      />
      {props.error && (
        <Typography
          hierarchy="body"
          size="xxs"
          weight="medium"
          class="col-span-full px-1 !fg-semantic-4"
        >
          {props.error}
        </Typography>
      )}
    </div>
  );
}
