import { callApi, OperationArgs } from "@/src/api";
import { activeURI } from "@/src/App";
import { Button } from "@/src/components/button";
import Icon from "@/src/components/icon";
import { TextInput } from "@/src/Form/fields/TextInput";
import { Header } from "@/src/layout/header";
import { createForm, required, reset } from "@modular-forms/solid";
import { useNavigate } from "@solidjs/router";
import { useQueryClient } from "@tanstack/solid-query";
import { Match, Switch } from "solid-js";
import toast from "solid-toast";
import { MachineAvatar } from "./avatar";
import { DynForm } from "@/src/Form/form";

type CreateMachineForm = OperationArgs<"create_machine">;

export function CreateMachine() {
  const navigate = useNavigate();
  const [formStore, { Form, Field }] = createForm<CreateMachineForm>({
    initialValues: {
      opts: {
        clan_dir: {
          identifier: activeURI() || "",
        },
        machine: {
          tags: ["all"],
          deploy: {
            targetHost: "",
          },
          name: "",
          description: "",
        },
      },
    },
  });

  const queryClient = useQueryClient();

  const handleSubmit = async (values: CreateMachineForm) => {
    const active_dir = activeURI();
    if (!active_dir) {
      toast.error("Open a clan to create the machine within");
      return;
    }

    console.log("submitting", values);

    const response = await callApi("create_machine", {
      opts: {
        ...values.opts,
        clan_dir: {
          identifier: active_dir,
        },
      },
    });

    if (response.status === "success") {
      toast.success(`Successfully created ${values.opts.machine.name}`);
      reset(formStore);

      queryClient.invalidateQueries({
        queryKey: [activeURI(), "list_machines"],
      });
      navigate("/machines");
    } else {
      toast.error(
        `Error: ${response.errors[0].message}. Machine ${values.opts.machine.name} could not be created`,
      );
    }
  };
  return (
    <>
      <Header title="Create Machine" />
      <div class="flex w-full p-4">
        <div class="mt-4 w-full self-stretch px-2">
          <Form onSubmit={handleSubmit} class="">
            <Field
              name="opts.machine.name"
              validate={[required("This field is required")]}
            >
              {(field, props) => (
                <>
                  <div class="flex justify-center">
                    <MachineAvatar name={field.value} />
                  </div>
                  <TextInput
                    inputProps={props}
                    value={`${field.value}`}
                    label={"name"}
                    error={field.error}
                    required
                    placeholder="New_machine"
                  />
                </>
              )}
            </Field>
            <Field name="opts.machine.description">
              {(field, props) => (
                <TextInput
                  inputProps={props}
                  value={`${field.value}`}
                  label={"description"}
                  error={field.error}
                  placeholder="My awesome machine"
                />
              )}
            </Field>
            <Field name="opts.machine.tags" type="string[]">
              {(field, props) => (
                <div class="p-2">
                  <DynForm
                    initialValues={{ tags: ["all"] }}
                    components={{
                      before: <div>Tags</div>,
                    }}
                    schema={{
                      type: "object",
                      properties: {
                        tags: {
                          type: "array",
                          items: {
                            title: "Tag",
                            type: "string",
                          },
                          uniqueItems: true,
                        },
                      },
                    }}
                  />
                </div>
              )}
            </Field>
            <div class="collapse collapse-arrow" tabindex="0">
              <input type="checkbox" />
              <div class="collapse-title link font-medium ">
                Deployment Settings
              </div>
              <div class="collapse-content">
                <Field name="opts.machine.deploy.targetHost">
                  {(field, props) => (
                    <>
                      <TextInput
                        inputProps={props}
                        value={`${field.value}`}
                        label={"Target"}
                        error={field.error}
                        placeholder="e.g. 192.168.188.64"
                      />
                    </>
                  )}
                </Field>
              </div>
            </div>
            <div class="mt-12 flex justify-end">
              <Button
                type="submit"
                disabled={formStore.submitting}
                startIcon={
                  formStore.submitting ? (
                    <Icon icon="Load" />
                  ) : (
                    <Icon icon="Plus" />
                  )
                }
              >
                <Switch fallback={<>Creating</>}>
                  <Match when={!formStore.submitting}>Create</Match>
                </Switch>
              </Button>
            </div>
          </Form>
        </div>
      </div>
    </>
  );
}
