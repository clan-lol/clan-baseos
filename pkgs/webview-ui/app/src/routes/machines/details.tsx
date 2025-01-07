import { callApi, SuccessData } from "@/src/api";
import { activeURI } from "@/src/App";
import { Button } from "@/src/components/button";
import Icon from "@/src/components/icon";
import { TextInput } from "@/src/Form/fields/TextInput";

import {
  createForm,
  FieldValues,
  getValue,
  getValues,
  setValue,
} from "@modular-forms/solid";
import { useParams } from "@solidjs/router";
import { createQuery } from "@tanstack/solid-query";
import { createSignal, For, Match, Show, Switch } from "solid-js";
import toast from "solid-toast";
import { MachineAvatar } from "./avatar";
import { Header } from "@/src/layout/header";
import { InputLabel } from "@/src/components/inputBase";
import { FieldLayout } from "@/src/Form/fields/layout";
import { Modal } from "@/src/components/modal";
import { Typography } from "@/src/components/Typography";
import { HardwareValues, HWStep } from "./install/hardware-step";
import { DiskStep, DiskValues } from "./install/disk-step";
import { SummaryStep } from "./install/summary-step";
import cx from "classnames";
import { SectionHeader } from "@/src/components/group";

type MachineFormInterface = MachineData & {
  sshKey?: File;
  disk?: string;
};

type MachineData = SuccessData<"get_inventory_machine_details">;

const steps: Record<StepIdx, string> = {
  "1": "Hardware detection",
  "2": "Disk schema",
  "3": "Installation",
};

type StepIdx = keyof AllStepsValues;

export interface AllStepsValues extends FieldValues {
  "1": HardwareValues;
  "2": DiskValues;
  "3": NonNullable<unknown>;
}

const LoadingBar = () => (
  <div
    class="h-3 w-80 overflow-hidden rounded-[3px] border-2 border-def-1"
    style={{
      background: `repeating-linear-gradient(
    45deg,
    #ccc,
    #ccc 8px,
    #eee 8px,
    #eee 16px
  )`,
      animation: "slide 25s linear infinite",
      "background-size": "200% 100%",
    }}
  ></div>
);

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
interface InstallMachineProps {
  name?: string;
  targetHost?: string | null;
  machine: MachineData;
}
const InstallMachine = (props: InstallMachineProps) => {
  const curr = activeURI();
  const { name } = props;
  if (!curr || !name) {
    return <span>No Clan selected</span>;
  }

  const [formStore, { Form, Field }] = createForm<AllStepsValues>();

  const [isDone, setIsDone] = createSignal<boolean>(false);
  const [isInstalling, setIsInstalling] = createSignal<boolean>(false);
  const [progressText, setProgressText] = createSignal<string>();

  const handleInstall = async (values: AllStepsValues) => {
    console.log("Installing", values);
    const curr_uri = activeURI();

    const target = values["1"].target;
    const diskValues = values["2"];

    if (!curr_uri) {
      return;
    }
    if (!props.name || !props.targetHost) {
      return;
    }

    const loading_toast = toast.loading(
      "Installing machine. Grab coffee (15min)...",
    );
    setIsInstalling(true);

    // props.machine.disk_
    const shouldRunDisk =
      JSON.stringify(props.machine.disk_schema?.placeholders) !==
      JSON.stringify(diskValues.placeholders);

    if (shouldRunDisk) {
      setProgressText("Setting up disk ... (1/5)");
      const disk_response = await callApi("set_machine_disk_schema", {
        base_path: curr_uri,
        machine_name: props.name,
        placeholders: diskValues.placeholders,
        schema_name: diskValues.schema,
        force: true,
      });

      if (disk_response.status === "error") {
        toast.error(
          `Failed to set disk schema: ${disk_response.errors[0].message}`,
        );
        setProgressText(
          "Failed to set disk schema. \n" + disk_response.errors[0].message,
        );
        return;
      }
    }

    setProgressText("Installing machine ... (2/5)");

    const installPromise = callApi("install_machine", {
      opts: {
        machine: {
          name: props.name,
          flake: {
            loc: curr_uri,
          },
        },
        target_host: target,
        password: "",
      },
    });

    // Next step
    await sleep(10 * 1000);
    setProgressText("Building machine ... (3/5)");
    await sleep(10 * 1000);
    setProgressText("Formatting remote disk ... (4/5)");
    await sleep(10 * 1000);
    setProgressText("Copying system ... (5/5)");
    await sleep(20 * 1000);
    setProgressText("Rebooting remote system ... ");
    await sleep(10 * 1000);

    const installResponse = await installPromise;

    toast.dismiss(loading_toast);

    if (installResponse.status === "error") {
      toast.error("Failed to install machine");
      setIsDone(true);
      setProgressText(
        "Failed to install machine. \n" + installResponse.errors[0].message,
      );
    }

    if (installResponse.status === "success") {
      toast.success("Machine installed successfully");
      setIsDone(true);
      setProgressText(
        "Machine installed successfully. Please unplug the usb stick and reboot the system.",
      );
    }
  };

  const [step, setStep] = createSignal<StepIdx>("1");

  const handleNext = () => {
    console.log("Next");
    setStep((c) => `${+c + 1}` as StepIdx);
  };
  const handlePrev = () => {
    console.log("Next");
    setStep((c) => `${+c - 1}` as StepIdx);
  };

  const Footer = () => (
    <div class="flex justify-between">
      <Button
        startIcon={<Icon icon="ArrowLeft" />}
        variant="light"
        type="button"
        onClick={handlePrev}
        disabled={step() === "1"}
      >
        Previous
      </Button>
      <Button
        endIcon={<Icon icon="ArrowRight" />}
        type="submit"
        // IMPORTANT: The step itself will try to submit and call the next step
        // onClick={(e: Event) => handleNext()}
      >
        Next
      </Button>
    </div>
  );

  return (
    <Switch
      fallback={
        <Form onSubmit={handleInstall}>
          {/* Register each step as form field */}
          {/* @ts-expect-error: object type is not statically supported */}
          <Field name="1">{(field, fieldProps) => <></>}</Field>
          {/* @ts-expect-error: object type is not statically supported */}
          <Field name="2">{(field, fieldProps) => <></>}</Field>

          {/* Modal Header */}
          <div class="select-none px-6 py-2">
            <Typography hierarchy="label" size="default">
              Install:{" "}
            </Typography>
            <Typography hierarchy="label" size="default" weight="bold">
              {props.name}
            </Typography>
          </div>
          {/* Stepper header */}
          <div class="flex items-center justify-evenly gap-2 border py-3 bg-def-3 border-def-2">
            <For each={Object.entries(steps)}>
              {([idx, label]) => (
                <div class="flex flex-col items-center gap-3 fg-def-1">
                  <Typography
                    classList={{
                      [cx("bg-inv-4 fg-inv-1")]: idx == step(),
                      [cx("bg-def-4 fg-def-1")]: idx < step(),
                    }}
                    color="inherit"
                    hierarchy="label"
                    size="default"
                    weight="bold"
                    class="flex size-6 items-center justify-center rounded-full text-center align-middle bg-def-1"
                  >
                    <Show
                      when={idx >= step()}
                      fallback={<Icon icon="Checkmark" class="size-5" />}
                    >
                      {idx}
                    </Show>
                  </Typography>
                  <Typography
                    color="inherit"
                    hierarchy="label"
                    size="xs"
                    weight="medium"
                    class="text-center align-top fg-def-3"
                    classList={{
                      [cx("!fg-def-1")]: idx == step(),
                    }}
                  >
                    {label}
                  </Typography>
                </div>
              )}
            </For>
          </div>

          <div class="flex flex-col gap-6 p-6">
            <Switch
              fallback={"Undefined content. This Step seems to not exist."}
            >
              <Match when={step() === "1"}>
                <HWStep
                  // @ts-expect-error: This cannot be undefined in this context.
                  machine_id={props.name}
                  // @ts-expect-error: This cannot be undefined in this context.
                  dir={activeURI()}
                  handleNext={(data) => {
                    const prev = getValue(formStore, "1");
                    setValue(formStore, "1", { ...prev, ...data });
                    handleNext();
                  }}
                  initial={
                    getValue(formStore, "1") || {
                      target: props.targetHost || "",
                      report: false,
                    }
                  }
                  footer={<Footer />}
                />
              </Match>
              <Match when={step() === "2"}>
                <DiskStep
                  // @ts-expect-error: This cannot be undefined in this context.
                  machine_id={props.name}
                  // @ts-expect-error: This cannot be undefined in this context.
                  dir={activeURI()}
                  footer={<Footer />}
                  handleNext={(data) => {
                    const prev = getValue(formStore, "2");
                    setValue(formStore, "2", { ...prev, ...data });
                    handleNext();
                  }}
                  // @ts-expect-error: The placeholder type is to wide
                  initial={{
                    ...props.machine.disk_schema,
                    ...getValue(formStore, "2"),
                    initialized: !!props.machine.disk_schema,
                  }}
                />
              </Match>
              <Match when={step() === "3"}>
                <SummaryStep
                  // @ts-expect-error: This cannot be undefined in this context.
                  machine_id={props.name}
                  // @ts-expect-error: This cannot be undefined in this context.
                  dir={activeURI()}
                  handleNext={() => handleNext()}
                  // @ts-expect-error: This cannot be known.
                  initial={getValues(formStore)}
                  footer={
                    <div class="flex justify-between">
                      <Button
                        startIcon={<Icon icon="ArrowLeft" />}
                        variant="light"
                        type="button"
                        onClick={handlePrev}
                        disabled={step() === "1"}
                      >
                        Previous
                      </Button>
                      <Button startIcon={<Icon icon="Flash" />}>Install</Button>
                    </div>
                  }
                />
              </Match>
            </Switch>
          </div>
        </Form>
      }
    >
      <Match when={isInstalling()}>
        <div class="flex h-96 w-[40rem] flex-col fg-inv-1">
          <div class="flex w-full gap-1 p-4 bg-inv-5">
            <Typography
              color="inherit"
              hierarchy="label"
              size="default"
              weight="medium"
            >
              Install:
            </Typography>
            <Typography
              color="inherit"
              hierarchy="label"
              size="default"
              weight="bold"
            >
              {props.name}
            </Typography>
          </div>
          <div class="flex h-full flex-col items-center gap-3 px-4 py-8 bg-inv-4 fg-inv-1">
            <Icon icon="ClanIcon" viewBox="0 0 72 89" class="size-20" />
            {isDone() && <LoadingBar />}
            <Typography
              hierarchy="label"
              size="default"
              weight="medium"
              color="inherit"
            >
              {progressText()}
            </Typography>
            <Button onClick={() => setIsInstalling(false)}>Cancel</Button>
          </div>
        </div>
      </Match>
    </Switch>
  );
};

interface MachineDetailsProps {
  initialData: MachineData;
}
const MachineForm = (props: MachineDetailsProps) => {
  const [formStore, { Form, Field }] =
    // TODO: retrieve the correct initial values from API
    createForm<MachineFormInterface>({
      initialValues: props.initialData,
    });

  const targetHost = () => getValue(formStore, "machine.deploy.targetHost");
  const machineName = () =>
    getValue(formStore, "machine.name") || props.initialData.machine.name;

  const [installModalOpen, setInstallModalOpen] = createSignal(false);

  const handleSubmit = async (values: MachineFormInterface) => {
    console.log("submitting", values);

    const curr_uri = activeURI();
    if (!curr_uri) {
      return;
    }

    const machine_response = await callApi("set_machine", {
      flake_url: curr_uri,
      machine_name: props.initialData.machine.name || "My machine",
      machine: {
        ...values.machine,
        // TODO: Remove this workaround
        tags: Array.from(
          values.machine.tags || props.initialData.machine.tags || [],
        ),
      },
    });
    if (machine_response.status === "error") {
      toast.error(
        `Failed to set machine: ${machine_response.errors[0].message}`,
      );
    }
    if (machine_response.status === "success") {
      toast.success("Machine set successfully");
    }

    return null;
  };

  const handleUpdate = async () => {
    const curr_uri = activeURI();
    if (!curr_uri) {
      return;
    }
    const machine = machineName();
    if (!machine) {
      toast.error("Machine is required");
      return;
    }

    const target = targetHost();
    if (!target) {
      toast.error("Target host is required");
      return;
    }

    const loading_toast = toast.loading("Updating machine...");
    const r = await callApi("update_machines", {
      base_path: curr_uri,
      machines: [
        {
          name: machine,
          deploy: {
            targetHost: target,
          },
        },
      ],
    });
    toast.dismiss(loading_toast);

    if (r.status === "error") {
      toast.error("Failed to update machine");
    }
    if (r.status === "success") {
      toast.success("Machine updated successfully");
    }
  };
  return (
    <>
      <div class="flex flex-col gap-6 p-4">
        <span class="mb-2 flex w-full justify-center">
          <MachineAvatar name={machineName()} />
        </span>
        <Form onSubmit={handleSubmit} class="flex flex-col gap-6">
          <Field name="machine.name">
            {(field, props) => (
              <TextInput
                inputProps={props}
                label="Name"
                value={field.value ?? ""}
                error={field.error}
                class="col-span-2"
                required
              />
            )}
          </Field>
          <Field name="machine.tags" type="string[]">
            {(field, props) => (
              <>
                <FieldLayout
                  label={<InputLabel>Tags</InputLabel>}
                  field={
                    <span class="col-span-10">
                      <For each={field.value}>
                        {(tag) => (
                          <span class="mx-2 w-fit rounded-full px-3 py-1 bg-inv-4 fg-inv-1">
                            {tag}
                          </span>
                        )}
                      </For>
                    </span>
                  }
                />
              </>
            )}
          </Field>
          <Field name="machine.description">
            {(field, props) => (
              <TextInput
                inputProps={props}
                label="Description"
                value={field.value ?? ""}
                error={field.error}
                class="col-span-2"
                required
              />
            )}
          </Field>
          <Field name="hw_config">
            {(field, props) => (
              <FieldLayout
                label={<InputLabel>Hardware Configuration</InputLabel>}
                field={<span>{field.value || "None"}</span>}
              />
            )}
          </Field>
          <Field name="disk_schema.schema_name">
            {(field, props) => (
              <>
                <FieldLayout
                  label={<InputLabel>Disk schema</InputLabel>}
                  field={<span>{field.value || "None"}</span>}
                />
              </>
            )}
          </Field>

          <div class="collapse collapse-arrow col-span-full" tabindex="0">
            <input type="checkbox" />
            <div class="collapse-title link px-0 text-xl ">
              Connection Settings
            </div>
            <div class="collapse-content">
              <Field name="machine.deploy.targetHost">
                {(field, props) => (
                  <TextInput
                    inputProps={props}
                    label="Target Host"
                    value={field.value ?? ""}
                    error={field.error}
                    class="col-span-2"
                    required
                  />
                )}
              </Field>
            </div>
          </div>

          {
            <div class="card-actions col-span-full justify-end">
              <Button
                type="submit"
                disabled={formStore.submitting || !formStore.dirty}
              >
                Save
              </Button>
            </div>
          }
        </Form>
      </div>

      <div class="card-body">
        <div class="divider"></div>

        <span class="text-xl text-primary-800">Actions</span>
        <div class="my-4 flex flex-col gap-6">
          <span class="max-w-md text-neutral">
            Installs the system for the first time. Used to bootstrap the remote
            device.
          </span>
          <div class="tooltip w-fit" data-tip="Machine must be online">
            <Button
              class="w-full"
              // disabled={!online()}
              onClick={() => {
                setInstallModalOpen(true);
              }}
              endIcon={<Icon icon="Flash" />}
            >
              Install
            </Button>
          </div>

          <Modal
            title={`Install machine`}
            open={installModalOpen()}
            handleClose={() => setInstallModalOpen(false)}
            class="min-w-[600px]"
          >
            <InstallMachine
              name={machineName()}
              targetHost={getValue(formStore, "machine.deploy.targetHost")}
              machine={props.initialData}
            />
          </Modal>

          <span class="max-w-md text-neutral">
            Update the system if changes should be synced after the installation
            process.
          </span>
          <div class="tooltip w-fit" data-tip="Machine must be online">
            <Button
              class="w-full"
              // disabled={!online()}
              onClick={() => handleUpdate()}
              endIcon={<Icon icon="Update" />}
            >
              Update
            </Button>
          </div>
        </div>
      </div>
    </>
  );
};

export const MachineDetails = () => {
  const params = useParams();
  const genericQuery = createQuery(() => ({
    queryKey: [
      activeURI(),
      "machine",
      params.id,
      "get_inventory_machine_details",
    ],
    queryFn: async () => {
      const curr = activeURI();
      if (curr) {
        const result = await callApi("get_inventory_machine_details", {
          flake_url: curr,
          machine_name: params.id,
        });
        if (result.status === "error") throw new Error("Failed to fetch data");
        return result.data;
      }
    },
  }));

  return (
    <>
      <Header title={`${params.id} machine`} showBack />
      <Show
        when={genericQuery.data}
        fallback={<span class="loading loading-lg"></span>}
      >
        {(data) => (
          <>
            <MachineForm initialData={data()} />
          </>
        )}
      </Show>
    </>
  );
};
