import { callApi } from "@/src/api";
import {
  createForm,
  SubmitHandler,
  validate,
  required,
  FieldValues,
} from "@modular-forms/solid";
import { createQuery } from "@tanstack/solid-query";
import { StepProps } from "./hardware-step";
import { SelectInput } from "@/src/Form/fields/Select";
import { Typography } from "@/src/components/Typography";
import { Group } from "@/src/components/group";

export interface DiskValues extends FieldValues {
  placeholders: {
    mainDisk: string;
  };
  schema: string;
  initialized: boolean;
}
export const DiskStep = (props: StepProps<DiskValues>) => {
  const [formStore, { Form, Field }] = createForm<DiskValues>({
    initialValues: { ...props.initial, schema: "single-disk" },
  });

  const handleSubmit: SubmitHandler<DiskValues> = async (values, event) => {
    console.log("Submit Disk", { values });
    const valid = await validate(formStore);
    console.log("Valid", valid);
    if (!valid) return;
    props.handleNext(values);
  };

  const diskSchemaQuery = createQuery(() => ({
    queryKey: [props.dir, props.machine_id, "disk_schemas"],
    queryFn: async () => {
      const result = await callApi("get_disk_schemas", {
        base_path: props.dir,
        machine_name: props.machine_id,
      });
      if (result.status === "error") throw new Error("Failed to fetch data");
      return result.data;
    },
  }));

  return (
    <Form
      onSubmit={handleSubmit}
      class="flex flex-col gap-6"
      noValidate={false}
    >
      <span class="flex flex-col gap-4">
        <Field name="schema" validate={required("Schema must be provided")}>
          {(field, fieldProps) => (
            <>
              <Typography
                hierarchy="body"
                size="default"
                weight="bold"
                class="capitalize"
              >
                {(field.value || "No schema selected").split("-").join(" ")}
              </Typography>
              <Typography
                hierarchy="body"
                size="xs"
                weight="medium"
                class="underline"
              >
                Change schema
              </Typography>
            </>
          )}
        </Field>
      </span>
      <Group>
        {props.initial?.initialized && "Disk has been initialized already"}
        <Field
          name="placeholders.mainDisk"
          validate={
            !props.initial?.initialized
              ? required("Disk must be provided")
              : undefined
          }
        >
          {(field, fieldProps) => (
            <SelectInput
              loading={diskSchemaQuery.isFetching}
              options={
                diskSchemaQuery.data?.["single-disk"].placeholders[
                  "mainDisk"
                ].options?.map((o) => ({ label: o, value: o })) || [
                  { label: "No options", value: "" },
                ]
              }
              error={field.error}
              label="Main Disk"
              value={field.value || ""}
              placeholder="Select a disk"
              selectProps={fieldProps}
              required={!props.initial?.initialized}
            />
          )}
        </Field>
      </Group>
      {props.footer}
    </Form>
  );
};
