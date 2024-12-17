import { Button } from "@/src/components/button";
import { InputBase, InputLabel } from "@/src/components/inputBase";
import { TextInput } from "@/src/Form/fields";
import { Header } from "@/src/layout/header";
import { createForm, required } from "@modular-forms/solid";

const disabled = [false, true];
const readOnly = [false, true];
const error = [false, true];

export const Components = () => {
  const [formStore, { Form, Field }] = createForm<{ ef: string }>({});
  return (
    <>
      <Header title="Components" />

      <div class="grid grid-cols-2 gap-4 p-4">
        <span class="col-span-2">Input </span>

        <span>Default</span>
        <span>Size S</span>

        {disabled.map((disabled) =>
          readOnly.map((readOnly) =>
            error.map((hasError) => (
              <>
                <span>
                  {[
                    disabled ? "Disabled" : "(default)",
                    readOnly ? "ReadOnly" : "",
                    hasError ? "Error" : "",
                  ]
                    .filter(Boolean)
                    .join(" + ")}
                </span>
                <InputBase
                  variant="outlined"
                  value="The Fox jumps!"
                  disabled={disabled}
                  error={hasError}
                  readonly={readOnly}
                />
              </>
            )),
          ),
        )}
        <span class="col-span-2">Input Ghost</span>
        {disabled.map((disabled) =>
          readOnly.map((readOnly) =>
            error.map((hasError) => (
              <>
                <span>
                  {[
                    disabled ? "Disabled" : "(default)",
                    readOnly ? "ReadOnly" : "",
                    hasError ? "Error" : "",
                  ]
                    .filter(Boolean)
                    .join(" + ")}
                </span>
                <InputBase
                  variant="ghost"
                  value="The Fox jumps!"
                  disabled={disabled}
                  error={hasError}
                  readonly={readOnly}
                />
              </>
            )),
          ),
        )}
        <span class="col-span-2">Input Label</span>
        <span>Default</span>
        <InputLabel>Labeltext</InputLabel>
        <span>Required</span>
        <InputLabel required>Labeltext</InputLabel>
        <span>Error</span>
        <InputLabel error>Labeltext</InputLabel>
        <span>Error + Reuired</span>
        <InputLabel error required>
          Labeltext
        </InputLabel>
        <span>Icon</span>
        <InputLabel help="Some Info">Labeltext</InputLabel>
        <span>Description</span>
        <InputLabel description="Some more words">Labeltext</InputLabel>
      </div>
      <div class="flex flex-col gap-2">
        <span class="col-span-full gap-4">Form Layout</span>
        <TextInput label="Label" value="Value" />
        <Form
          onSubmit={() => {
            console.log("Nothing");
          }}
        >
          <Field
            name="ef"
            validate={required(
              "This field is required very long descriptive error message",
            )}
          >
            {(field, inputProps) => (
              <TextInput
                label="Write something"
                error={field.error}
                required
                value={field.value || ""}
                inputProps={inputProps}
              />
            )}
          </Field>
          <Button>Submit</Button>
        </Form>
        <TextInput label="Label" required value="Value" />
      </div>
    </>
  );
};
