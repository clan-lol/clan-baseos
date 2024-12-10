import { callApi, SuccessData, SuccessQuery } from "@/src/api";
import { activeURI } from "@/src/App";
import { BackButton } from "@/src/components/BackButton";
import { Button } from "@/src/components/button";
import { FileInput } from "@/src/components/FileInput";
import Icon from "@/src/components/icon";
import { TextInput } from "@/src/components/TextInput";
import { selectSshKeys } from "@/src/hooks";
import {
  createForm,
  FieldValues,
  getValue,
  setValue,
} from "@modular-forms/solid";
import { useParams } from "@solidjs/router";
import { createQuery } from "@tanstack/solid-query";
import { createSignal, For, Show } from "solid-js";
import toast from "solid-toast";
import { MachineAvatar } from "./avatar";

type MachineFormInterface = MachineData & {
  sshKey?: File;
  disk?: string;
};

type MachineData = SuccessData<"get_inventory_machine_details">;

type Disks = SuccessQuery<"show_block_devices">["data"]["blockdevices"];

interface InstallForm extends FieldValues {
  disk?: string;
}

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
        flake: {
          loc: curr_uri,
        },
        machine: props.name,
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
    e.preventDefault();
    const curr_uri = activeURI();
    const disk = getValue(formStore, "disk");
    const disk_id = props.disks.find((d) => d.name === disk)?.id_link;
    if (!curr_uri || !disk_id || !props.name) {
      return;
    }
  };

  const generateReport = async (e: Event) => {
    e.preventDefault();
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
        backend: "NIXOS_FACTER",
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
  return (
    <>
      <Form onSubmit={handleInstall}>
        <h3 class="text-lg font-bold">
          <span class="font-normal">Install: </span>
          {props.name}
        </h3>
        <p class="py-4">
          Install the system for the first time. This will erase the disk and
          bootstrap a new device.
        </p>

        <div class="flex flex-col">
          <div class="text-lg font-semibold">Hardware detection</div>
          <div class="flex justify-between py-4">
            <div class="">
              <Button
                variant="light"
                size="s"
                class="w-full"
                onclick={generateReport}
                endIcon={<Icon icon="Report" />}
              >
                Run hardware Report
              </Button>
            </div>
          </div>
          <div class="text-lg font-semibold">Disk schema</div>
          <div class="flex justify-between py-4">
            <div class="">
              <Button
                variant="light"
                size="s"
                class="w-full"
                onclick={generateReport}
                endIcon={<Icon icon="Flash" />}
              >
                Select disk Schema
              </Button>
            </div>
          </div>
        </div>

        <Field name="disk">{(field, fieldProps) => "disk"}</Field>
        <div role="alert" class="alert my-4">
          <span class="material-icons">info</span>
          <div>
            <div class="font-semibold">Summary:</div>
            <div class="mb-2">
              Install to <b>{props.targetHost}</b> using{" "}
              <b>{props.sshKey?.name || "default ssh key"}</b> for
              authentication.
            </div>
            This may take ~15 minutes depending on the initial closure and the
            environmental setup.
          </div>
        </div>
        <div class="modal-action">
          <Show
            when={confirmDisk()}
            fallback={
              <Button
                class="btn btn-primary btn-wide"
                onClick={handleDiskConfirm}
                disabled={!hasDisk()}
                endIcon={<Icon icon="Flash" />}
              >
                Install
              </Button>
            }
          >
            <Button
              class="w-full"
              type="submit"
              endIcon={<Icon icon="Flash" />}
            >
              Install
            </Button>
          </Show>
          <form method="dialog">
            <Button
              variant="light"
              onClick={() => setConfirmDisk(false)}
              class="btn"
            >
              Close
            </Button>
          </form>
        </div>
      </Form>
    </>
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
      <Form onSubmit={handleSubmit}>
        <div class="card-body">
          <span class="text-xl text-primary-800">General</span>
          <MachineAvatar name={machineName()} />
          <Field name="machine.name">
            {(field, props) => (
              <TextInput
                formStore={formStore}
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
              <For each={field.value}>
                {(tag) => (
                  <label class="p-1">
                    Tags
                    <span class="mx-2 w-fit rounded-full px-3 py-1 bg-inv-4 fg-inv-1">
                      {tag}
                    </span>
                  </label>
                )}
              </For>
            )}
          </Field>
          <Field name="machine.description">
            {(field, props) => (
              <TextInput
                formStore={formStore}
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
              <label>Hardware report: {field.value || "None"}</label>
            )}
          </Field>
          <Field name="disk_schema">
            {(field, props) => (
              <span>Disk schema: {field.value || "None"}</span>
            )}
          </Field>

          <div class="collapse collapse-arrow" tabindex="0">
            <input type="checkbox" />
            <div class="collapse-title link px-0 text-xl ">
              Connection Settings
            </div>
            <div class="collapse-content">
              <Field name="machine.deploy.targetHost">
                {(field, props) => (
                  <TextInput
                    formStore={formStore}
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
            <div class="card-actions justify-end">
              <Button
                type="submit"
                disabled={formStore.submitting || !formStore.dirty}
              >
                Save
              </Button>
            </div>
          }
        </div>
      </Form>

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
                const modal = document.getElementById(
                  "install_modal",
                ) as HTMLDialogElement | null;
                modal?.showModal();
              }}
              endIcon={<Icon icon="Flash" />}
            >
              Install
            </Button>
          </div>

          <dialog id="install_modal" class="modal backdrop:bg-transparent">
            <div class="modal-box w-11/12 max-w-5xl">
              <InstallMachine
                name={machineName()}
                sshKey={sshKey()}
                targetHost={getValue(formStore, "machine.deploy.targetHost")}
                disks={[]}
              />
            </div>
          </dialog>

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
    <div class="card">
      <BackButton />
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
          <div class="flex gap-4">
            <Field name={`networks.${idx()}.ssid`}>
              {(field, props) => (
                <TextInput
                  formStore={formStore}
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
                  formStore={formStore}
                  inputProps={props}
                  label="Password"
                  value={field.value ?? ""}
                  error={field.error}
                  type="password"
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
