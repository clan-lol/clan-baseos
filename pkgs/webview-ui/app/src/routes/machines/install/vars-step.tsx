import { callApi } from "@/src/api";
import {
  createForm,
  SubmitHandler,
  validate,
  FieldValues,
} from "@modular-forms/solid";
import { createQuery } from "@tanstack/solid-query";
import { StepProps } from "./hardware-step";
import { Typography } from "@/src/components/Typography";
import { Group } from "@/src/components/group";
import { For, Match, Show, Switch } from "solid-js";

export type VarsValues = FieldValues & Record<string, string>;

export const VarsStep = (props: StepProps<VarsValues>) => {
  const [formStore, { Form, Field }] = createForm<VarsValues>({
    initialValues: { ...props.initial, schema: "single-disk" },
  });

  const handleSubmit: SubmitHandler<VarsValues> = async (values, event) => {
    console.log("Submit Disk", { values });
    const valid = await validate(formStore);
    console.log("Valid", valid);
    if (!valid) return;
    props.handleNext(values);
  };

  const generatorsQuery = createQuery(() => ({
    queryKey: [props.dir, props.machine_id, "generators"],
    queryFn: async () => {
      const result = await callApi("get_generators", {
        base_dir: props.dir,
        machine_name: props.machine_id,
      });
      if (result.status === "error") throw new Error("Failed to fetch data");
      return result.data;
    },
  }));

  return (
    <Form
      onSubmit={handleSubmit}
      class="flex h-full flex-col gap-6"
      noValidate={false}
    >
      <div class="max-h-[calc(100vh-20rem)] overflow-y-scroll">
        <div class="flex h-full flex-col gap-6 p-4">
          <Switch>
            <Match when={generatorsQuery.isLoading}>Loading ...</Match>
            <Match when={generatorsQuery.data}>
              {(generators) => (
                <For each={generators()}>
                  {(generator) => (
                    <Group>
                      <Typography hierarchy="label" size="default">
                        {generator.name}
                      </Typography>
                      <div>
                        Bound to module (shared):{" "}
                        {generator.share ? "True" : "False"}
                      </div>
                      <For each={generator.prompts}>
                        {(f) => (
                          <Group>
                            <Typography hierarchy="label" size="s">
                              {!f.previous_value ? "Required" : "Optional"}
                            </Typography>
                            <Typography hierarchy="label" size="s">
                              {f.name}
                            </Typography>
                          </Group>
                        )}
                      </For>
                    </Group>
                  )}
                </For>
              )}
            </Match>
          </Switch>
        </div>
      </div>
      <Show when={generatorsQuery.isFetched}>{props.footer}</Show>
    </Form>
  );
};
