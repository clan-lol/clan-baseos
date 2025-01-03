import { callApi, SuccessData, SuccessQuery } from "@/src/api";
import { activeURI } from "@/src/App";
import { Button } from "@/src/components/button";
import { FileInput } from "@/src/components/FileInput";
import Icon, { IconVariant } from "@/src/components/icon";
import { TextInput } from "@/src/Form/fields/TextInput";
import { selectSshKeys } from "@/src/hooks";
import {
  createForm,
  FieldValues,
  getValue,
  setValue,
} from "@modular-forms/solid";
import { useParams } from "@solidjs/router";
import { createQuery } from "@tanstack/solid-query";
import { createSignal, For, JSX, Match, Show, Switch } from "solid-js";
import toast from "solid-toast";
import { MachineAvatar } from "./avatar";
import { Header } from "@/src/layout/header";
import { InputLabel } from "@/src/components/inputBase";
import { FieldLayout } from "@/src/Form/fields/layout";
import { Modal } from "@/src/components/modal";
import { Typography } from "@/src/components/Typography";
import cx from "classnames";
import { SelectInput } from "@/src/Form/fields/Select";
import { HWStep } from "./install/hardware-step";

type MachineFormInterface = MachineData & {
  sshKey?: File;
  disk?: string;
};

type MachineData = SuccessData<"get_inventory_machine_details">;

type Disks = SuccessQuery<"show_block_devices">["data"]["blockdevices"];

interface InstallForm extends FieldValues {
  disk?: string;
}

interface GroupProps {
  children: JSX.Element;
}
export const Group = (props: GroupProps) => (
  <div class="flex flex-col  gap-8 rounded-md border px-4 py-5 bg-def-2 border-def-2">
    {props.children}
  </div>
);

type AdmonitionVariant = "attention" | "danger";
interface SectionHeaderProps {
  variant: AdmonitionVariant;
  headline: JSX.Element;
}
const variantColorsMap: Record<AdmonitionVariant, string> = {
  attention: cx("bg-[#9BD8F2] fg-def-1"),
  danger: cx("bg-semantic-2 fg-semantic-2"),
};

const variantIconColorsMap: Record<AdmonitionVariant, string> = {
  attention: cx("fg-def-1"),
  danger: cx("fg-semantic-3"),
};

const variantIconMap: Record<AdmonitionVariant, IconVariant> = {
  attention: "Attention",
  danger: "Warning",
};

export const SectionHeader = (props: SectionHeaderProps) => (
  <div
    class={cx(
      "flex items-center gap-3 rounded-md px-3 py-2",
      variantColorsMap[props.variant],
    )}
  >
    {
      <Icon
        icon={variantIconMap[props.variant]}
        class={cx("size-5", variantIconColorsMap[props.variant])}
      />
    }
    {props.headline}
  </div>
);

const steps = {
  "1": "Hardware detection",
  "2": "Disk schema",
  "3": "Installation",
};

interface SectionProps {
  children: JSX.Element;
}
const Section = (props: SectionProps) => (
  <div class="flex flex-col gap-3">{props.children}</div>
);

interface InstallMachineProps {
  name?: string;
  targetHost?: string | null;
  sshKey?: File;
  disks: Disks;
}
const InstallMachine = (props: InstallMachineProps) => {
  const curr = activeURI();
  const { name } = props;
  if (!curr || !name) {
    return <span>No Clan selected</span>;
  }

  const diskPlaceholder = "Select the boot disk of the remote machine";

  const [formStore, { Form, Field }] = createForm<InstallForm>();

  const hasDisk = () => getValue(formStore, "disk") !== diskPlaceholder;

  const [confirmDisk, setConfirmDisk] = createSignal(!hasDisk());

  const handleInstall = async (values: InstallForm) => {
    console.log("Installing", values);
    const curr_uri = activeURI();
    if (!curr_uri) {
      return;
    }
    if (!props.name || !props.targetHost) {
      return;
    }

    const loading_toast = toast.loading(
      "Installing machine. Grab coffee (15min)...",
    );
    const r = await callApi("install_machine", {
      opts: {
        machine: {
          name: props.name,
          flake: {
            loc: curr_uri,
          },
        },
        target_host: props.targetHost,
        password: "",
      },
    });
    toast.dismiss(loading_toast);

    if (r.status === "error") {
      toast.error("Failed to install machine");
    }
    if (r.status === "success") {
      toast.success("Machine installed successfully");
    }
  };

  const handleDiskConfirm = async (e: Event) => {
    const curr_uri = activeURI();
    const disk = getValue(formStore, "disk");
    const disk_id = props.disks.find((d) => d.name === disk)?.id_link;
    if (!curr_uri || !disk_id || !props.name) {
      return;
    }
  };
  const [stepsDone, setStepsDone] = createSignal<StepIdx[]>([]);

  const generateReport = async (e: Event) => {
    const curr_uri = activeURI();
    if (!curr_uri || !props.name) {
      return;
    }

    const loading_toast = toast.loading("Generating hardware report...");
    const r = await callApi("generate_machine_hardware_info", {
      opts: {
        flake: { loc: curr_uri },
        machine: props.name,
        keyfile: props.sshKey?.name,
        target_host: props.targetHost,
        backend: "nixos-facter",
      },
    });
    toast.dismiss(loading_toast);
    // TODO: refresh the machine details

    if (r.status === "error") {
      toast.error(`Failed to generate report. ${r.errors[0].message}`);
    }
    if (r.status === "success") {
      toast.success("Report generated successfully");
    }
  };

  type StepIdx = keyof typeof steps;
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
    <div>
      <div class="select-none px-6 py-2">
        <Typography hierarchy="label" size="default">
          Install:{" "}
        </Typography>
        <Typography hierarchy="label" size="default" weight="bold">
          {props.name}
        </Typography>
      </div>
      {/* Stepper container */}
      <div class="flex items-center justify-evenly gap-2 border py-3 bg-def-3 border-def-2">
        {/* A Step with a circle a number inside. Label is below */}
        <For each={Object.entries(steps)}>
          {([idx, label]) => (
            <div class="flex flex-col items-center gap-3 fg-def-1">
              <Typography
                classList={{
                  [cx("bg-inv-4 fg-inv-1")]: idx == step(),
                  [cx("bg-def-4 fg-def-1")]: idx < step(),
                }}
                useExternColor={true}
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
                useExternColor={true}
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
        <Switch fallback={"Undefined content. This Step seems to not exist."}>
          <Match when={step() === "1"}>
            <HWStep
              initial={{
                target: props.targetHost || "",
              }}
              machine_id={props.name}
              dir={activeURI()}
              handleNext={() => handleNext()}
              footer={<Footer />}
            />
          </Match>
          <Match when={step() === "2"}>
            <span class="flex flex-col gap-4">
              <Typography hierarchy="body" size="default" weight="bold">
                Single Disk
              </Typography>
              <Typography
                hierarchy="body"
                size="xs"
                weight="medium"
                class="underline"
              >
                Change schema
              </Typography>
            </span>
            <Group>
              <SelectInput required label="Main Disk" options={[]} value={[]} />
            </Group>
            <Footer />
          </Match>
          <Match when={step() === "3"}>
            <Section>
              <Typography
                hierarchy="label"
                size="xs"
                weight="medium"
                class="uppercase"
              >
                Hardware Report
              </Typography>
              <Group>
                <FieldLayout
                  label={<InputLabel>Target</InputLabel>}
                  field={
                    <Typography hierarchy="body" size="xs" weight="bold">
                      192.157.124.81
                    </Typography>
                  }
                ></FieldLayout>
              </Group>
            </Section>
            <Section>
              <Typography
                hierarchy="label"
                size="xs"
                weight="medium"
                class="uppercase"
              >
                Disk Configuration
              </Typography>
              <Group>
                <FieldLayout
                  label={<InputLabel>Disk Layout</InputLabel>}
                  field={
                    <Typography hierarchy="body" size="xs" weight="bold">
                      Single Disk
                    </Typography>
                  }
                ></FieldLayout>
                <hr class="h-px w-full border-none bg-acc-3"></hr>
                <FieldLayout
                  label={<InputLabel>Main Disk</InputLabel>}
                  field={
                    <Typography hierarchy="body" size="xs" weight="bold">
                      Samsung evo 850 efkjhasd
                    </Typography>
                  }
                ></FieldLayout>
              </Group>
            </Section>
            <SectionHeader
              variant="danger"
              headline={
                <span>
                  <Typography
                    hierarchy="body"
                    size="s"
                    weight="bold"
                    useExternColor
                  >
                    Setup your device.
                  </Typography>
                  <Typography
                    hierarchy="body"
                    size="s"
                    weight="medium"
                    useExternColor
                  >
                    This will erase the disk and bootstrap fresh.
                  </Typography>
                </span>
              }
            />
            <Footer></Footer>
            <Button startIcon={<Icon icon="Flash" />}>Install</Button>
          </Match>
        </Switch>
      </div>
    </div>
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

  const sshKey = () => getValue(formStore, "sshKey");
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
      <div class="card-body">
        <span class="text-xl text-primary-800">General</span>
        <MachineAvatar name={machineName()} />
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
          <Field name="disk_schema">
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
              <Field name="sshKey" type="File">
                {(field, props) => (
                  <>
                    <FileInput
                      {...props}
                      onClick={async (event) => {
                        event.preventDefault(); // Prevent the native file dialog from opening
                        const input = event.target;
                        const files = await selectSshKeys();

                        // Set the files
                        Object.defineProperty(input, "files", {
                          value: files,
                          writable: true,
                        });
                        // Define the files property on the input element
                        const changeEvent = new Event("input", {
                          bubbles: true,
                          cancelable: true,
                        });
                        input.dispatchEvent(changeEvent);
                      }}
                      placeholder={"When empty the default key(s) will be used"}
                      value={field.value}
                      error={field.error}
                      helperText="Provide the SSH key used to connect to the machine"
                      label="SSH Key"
                    />
                  </>
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
              sshKey={sshKey()}
              targetHost={getValue(formStore, "machine.deploy.targetHost")}
              disks={[]}
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
      <div class="card">
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
      </div>
    </>
  );
};

interface Wifi extends FieldValues {
  name: string;
  ssid?: string;
  password?: string;
}

interface WifiForm extends FieldValues {
  networks: Wifi[];
}

interface MachineWifiProps {
  base_url: string;
  machine_name: string;
  initialData: Wifi[];
}
function WifiModule(props: MachineWifiProps) {
  // You can use formData to initialize your form fields:
  // const initialFormState = formData();

  const [formStore, { Form, Field }] = createForm<WifiForm>({
    initialValues: {
      networks: props.initialData,
    },
  });

  const [nets, setNets] = createSignal<1[]>(
    new Array(props.initialData.length || 1).fill(1),
  );

  const handleSubmit = async (values: WifiForm) => {
    const networks = values.networks
      .filter((i) => i.ssid)
      .reduce(
        (acc, curr) => ({
          ...acc,
          [curr.ssid || ""]: { ssid: curr.ssid, password: curr.password },
        }),
        {},
      );

    console.log("submitting", values, networks);
    // const r = await callApi("set_iwd_service_for_machine", {
    //   base_url: props.base_url,
    //   machine_name: props.machine_name,
    //   networks: networks,
    // });
    // if (r.status === "error") {
    toast.error("Failed to set wifi. Feature disabled temporarily");
    // }
    // if (r.status === "success") {
    //   toast.success("Wifi set successfully");
    // }
  };

  return (
    <Form onSubmit={handleSubmit}>
      <span class="text-neutral">Preconfigure wireless networks</span>
      <For each={nets()}>
        {(_, idx) => (
          <div class="grid grid-cols-2">
            <Field name={`networks.${idx()}.ssid`}>
              {(field, props) => (
                <TextInput
                  inputProps={props}
                  label="Name"
                  value={field.value ?? ""}
                  error={field.error}
                  required
                />
              )}
            </Field>
            <Field name={`networks.${idx()}.password`}>
              {(field, props) => (
                <TextInput
                  inputProps={props}
                  label="Password"
                  value={field.value ?? ""}
                  error={field.error}
                  // todo
                  // type="password"
                  required
                />
              )}
            </Field>
            <Button
              variant="light"
              class="self-end"
              type="button"
              onClick={() => {
                setNets((c) => c.filter((_, i) => i !== idx()));
                setValue(formStore, `networks.${idx()}.ssid`, undefined);
                setValue(formStore, `networks.${idx()}.password`, undefined);
              }}
              startIcon={<Icon icon="Trash" />}
            ></Button>
          </div>
        )}
      </For>
      <Button
        class="btn btn-ghost btn-sm my-1 flex items-center justify-center"
        onClick={(e) => {
          setNets([...nets(), 1]);
        }}
        type="button"
        startIcon={<Icon icon="Plus" />}
      >
        Add Network
      </Button>
      {
        <div class="card-actions mt-4 justify-end">
          <Button
            type="submit"
            disabled={formStore.submitting || !formStore.dirty}
          >
            Save
          </Button>
        </div>
      }
    </Form>
  );
}
