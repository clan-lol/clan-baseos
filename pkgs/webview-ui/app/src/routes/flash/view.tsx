import { callApi } from "@/src/api";
import { Button } from "@/src/components/button";
import { FileInput } from "@/src/components/FileInput";
import Icon from "@/src/components/icon";

import { Typography } from "@/src/components/Typography";
import { Header } from "@/src/layout/header";

import { SelectInput } from "@/src/Form/fields/Select";
import { TextInput } from "@/src/Form/fields/TextInput";
import {
  createForm,
  required,
  FieldValues,
  setValue,
  getValue,
  getValues,
} from "@modular-forms/solid";
import { createQuery } from "@tanstack/solid-query";
import { createEffect, createSignal, For, Show } from "solid-js";
import toast from "solid-toast";
import { FieldLayout } from "@/src/Form/fields/layout";
import { InputLabel } from "@/src/components/inputBase";
import { Modal } from "@/src/components/modal";

interface Wifi extends FieldValues {
  ssid: string;
  password: string;
}

interface FlashFormValues extends FieldValues {
  machine: {
    devicePath: string;
    flake: string;
  };
  disk: string;
  language: string;
  keymap: string;
  wifi: Wifi[];
  sshKeys: File[];
}

export const Flash = () => {
  const [formStore, { Form, Field }] = createForm<FlashFormValues>({
    initialValues: {
      machine: {
        flake: "git+https://git.clan.lol/clan/clan-core",
        devicePath: "flash-installer",
      },
      language: "en_US.UTF-8",
      keymap: "en",
    },
  });

  /* ==== WIFI NETWORK ==== */
  const [wifiNetworks, setWifiNetworks] = createSignal<Wifi[]>([]);
  const [passwordVisibility, setPasswordVisibility] = createSignal<boolean[]>(
    [],
  );

  createEffect(() => {
    const formWifi = getValue(formStore, "wifi");
    if (formWifi !== undefined) {
      setWifiNetworks(formWifi as Wifi[]);
      setPasswordVisibility(new Array(formWifi.length).fill(false));
    }
  });

  const addWifiNetwork = () => {
    setWifiNetworks((c) => {
      const res = [...c, { ssid: "", password: "" }];
      setValue(formStore, "wifi", res);
      return res;
    });
    setPasswordVisibility((c) => [...c, false]);
  };

  const removeWifiNetwork = (index: number) => {
    const updatedNetworks = wifiNetworks().filter((_, i) => i !== index);
    setWifiNetworks(updatedNetworks);
    const updatedVisibility = passwordVisibility().filter(
      (_, i) => i !== index,
    );
    setPasswordVisibility(updatedVisibility);
    setValue(formStore, "wifi", updatedNetworks);
  };

  const togglePasswordVisibility = (index: number) => {
    const updatedVisibility = [...passwordVisibility()];
    updatedVisibility[index] = !updatedVisibility[index];
    setPasswordVisibility(updatedVisibility);
  };
  /* ==== END OF WIFI NETWORK ==== */

  const deviceQuery = createQuery(() => ({
    queryKey: ["block_devices"],
    queryFn: async () => {
      const result = await callApi("show_block_devices", {});
      if (result.status === "error") throw new Error("Failed to fetch data");
      return result.data;
    },
    staleTime: 1000 * 60 * 1, // 1 minutes
  }));

  const keymapQuery = createQuery(() => ({
    queryKey: ["list_keymaps"],
    queryFn: async () => {
      const result = await callApi("list_possible_keymaps", {});
      if (result.status === "error") throw new Error("Failed to fetch data");
      return result.data;
    },
    staleTime: Infinity,
  }));

  const langQuery = createQuery(() => ({
    queryKey: ["list_languages"],
    queryFn: async () => {
      const result = await callApi("list_possible_languages", {});
      if (result.status === "error") throw new Error("Failed to fetch data");
      return result.data;
    },
    staleTime: Infinity,
  }));

  /**
   * Opens the custom file dialog
   * Returns a native FileList to allow interaction with the native input type="file"
   */
  const selectSshKeys = async (): Promise<FileList> => {
    const dataTransfer = new DataTransfer();

    const response = await callApi("open_file", {
      file_request: {
        title: "Select SSH Key",
        mode: "open_multiple_files",
        filters: { patterns: ["*.pub"] },
        initial_folder: "~/.ssh",
      },
    });
    if (response.status === "success" && response.data) {
      // Add synthetic files to the DataTransfer object
      // FileList cannot be instantiated directly.
      response.data.forEach((filename) => {
        dataTransfer.items.add(new File([], filename));
      });
    }
    return dataTransfer.files;
  };
  const [confirmOpen, setConfirmOpen] = createSignal(false);
  const [isFlashing, setFlashing] = createSignal(false);

  const handleSubmit = (values: FlashFormValues) => {
    setConfirmOpen(true);
  };
  const handleConfirm = async () => {
    // Wait for the flash to complete
    const values = getValues(formStore) as FlashFormValues;
    setFlashing(true);
    console.log("Confirmed flash:", values);
    try {
      await toast.promise(
        callApi("flash_machine", {
          machine: {
            name: values.machine.devicePath,
            flake: {
              loc: values.machine.flake,
            },
          },
          mode: "format",
          disks: [{ name: "main", device: values.disk }],
          system_config: {
            language: values.language,
            keymap: values.keymap,
            ssh_keys_path: values.sshKeys.map((file) => file.name),
          },
          dry_run: false,
          write_efi_boot_entries: false,
          debug: false,
          graphical: true,
        }),
        {
          error: (errors) => `Error flashing disk: ${errors}`,
          loading: "Flashing ... This may take up to 15minutes.",
          success: "Disk flashed successfully",
        },
      );
    } catch (error) {
      toast.error(`Error could not flash disk: ${error}`);
    } finally {
      setFlashing(false);
    }
    setConfirmOpen(false);
  };

  return (
    <>
      <Header title="Flash installer" />
      <Modal
        open={confirmOpen() || isFlashing()}
        handleClose={() => !isFlashing() && setConfirmOpen(false)}
        title="Confirm"
      >
        <div class="flex flex-col gap-4 p-4">
          <div class="flex flex-col justify-between rounded-sm border p-4 align-middle text-red-900 border-def-2">
            <Typography
              hierarchy="label"
              weight="medium"
              size="default"
              class="flex-wrap break-words pr-4"
            >
              Warning: All data will be lost.
            </Typography>
            <Typography
              hierarchy="label"
              weight="bold"
              size="default"
              class="flex-wrap break-words pr-4"
            >
              Selected disk: '{getValue(formStore, "disk")}'
            </Typography>
          </div>
          <div class="flex w-full justify-between">
            <Button
              disabled={isFlashing()}
              variant="light"
              onClick={() => setConfirmOpen(false)}
            >
              Cancel
            </Button>
            <Button disabled={isFlashing()} onClick={handleConfirm}>
              Confirm
            </Button>
          </div>
        </div>
      </Modal>
      <div class="p-4">
        <Typography tag="p" hierarchy="body" size="default" color="primary">
          USB Utility image.
        </Typography>
        <Typography tag="p" hierarchy="body" size="default" color="secondary">
          Will make bootstrapping new machines easier by providing secure remote
          connection to any machine when plugged in.
        </Typography>
        <Form onSubmit={handleSubmit}>
          <div class="my-4">
            <Field name="sshKeys" type="File[]">
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
                    value={field.value}
                    error={field.error}
                    helperText="Provide your SSH public key. For secure and passwordless SSH connections."
                    label="Authorized SSH Keys"
                    multiple
                    required
                  />
                </>
              )}
            </Field>
          </div>

          <Field name="disk" validate={[required("This field is required")]}>
            {(field, props) => (
              <SelectInput
                loading={deviceQuery.isFetching}
                selectProps={props}
                label="Flash Disk"
                labelProps={{
                  labelAction: (
                    <Button
                      disabled={isFlashing()}
                      class="ml-auto"
                      variant="ghost"
                      size="s"
                      type="button"
                      startIcon={<Icon icon="Update" />}
                      onClick={() => deviceQuery.refetch()}
                    />
                  ),
                }}
                value={field.value || ""}
                error={field.error}
                required
                placeholder="Select a drive where the clan-installer will be flashed to"
                options={
                  deviceQuery.data?.blockdevices.map((d) => ({
                    value: d.path,
                    label: `${d.path} -- ${d.size} bytes`,
                  })) || []
                }
              />
            )}
          </Field>

          {/* WiFi Networks */}
          <div class="my-4 py-2">
            <FieldLayout
              label={<InputLabel class="mb-4">Networks</InputLabel>}
              field={
                <>
                  <Button
                    type="button"
                    size="s"
                    variant="light"
                    onClick={addWifiNetwork}
                    startIcon={<Icon icon="Plus" />}
                  >
                    WiFi Network
                  </Button>
                </>
              }
            />
            <For each={wifiNetworks()}>
              {(network, index) => (
                <div class="flex w-full gap-2">
                  <div class="mb-2 grid w-full grid-cols-6 gap-2 align-middle">
                    <Field
                      name={`wifi.${index()}.ssid`}
                      validate={[required("SSID is required")]}
                    >
                      {(field, props) => (
                        <TextInput
                          inputProps={props}
                          label="SSID"
                          value={field.value ?? ""}
                          error={field.error}
                          class="col-span-full "
                          required
                        />
                      )}
                    </Field>
                    <Field
                      name={`wifi.${index()}.password`}
                      validate={[required("Password is required")]}
                    >
                      {(field, props) => (
                        <TextInput
                          class="col-span-full"
                          inputProps={{
                            ...props,
                            type: passwordVisibility()[index()]
                              ? "text"
                              : "password",
                          }}
                          label="Password"
                          value={field.value ?? ""}
                          error={field.error}
                          // adornment={{
                          //   position: "end",
                          //   content: (
                          //     <Button
                          //       variant="light"
                          //       type="button"
                          //       class="flex justify-center opacity-70"
                          //       onClick={() =>
                          //         togglePasswordVisibility(index())
                          //       }
                          //       startIcon={
                          //         passwordVisibility()[index()] ? (
                          //           <Icon icon="EyeClose" />
                          //         ) : (
                          //           <Icon icon="EyeOpen" />
                          //         )
                          //       }
                          //     ></Button>
                          //   ),
                          // }}
                          required
                        />
                      )}
                    </Field>
                  </div>
                  <Button
                    type="button"
                    variant="light"
                    class="h-10"
                    size="s"
                    onClick={() => removeWifiNetwork(index())}
                    startIcon={<Icon icon="Trash" />}
                  ></Button>
                </div>
              )}
            </For>
          </div>

          <div class="collapse collapse-arrow" tabindex="0">
            <input type="checkbox" />
            <div class="collapse-title px-0">
              <InputLabel class="mb-4">Advanced</InputLabel>
            </div>
            <div class="collapse-content">
              <Field
                name="machine.flake"
                validate={[required("This field is required")]}
              >
                {(field, props) => (
                  <>
                    <TextInput
                      inputProps={props}
                      label="Source (flake URL)"
                      value={String(field.value)}
                      error={field.error}
                      required
                    />
                  </>
                )}
              </Field>
              <Field
                name="machine.devicePath"
                validate={[required("This field is required")]}
              >
                {(field, props) => (
                  <>
                    <TextInput
                      inputProps={props}
                      label="Image Name (attribute name)"
                      value={String(field.value)}
                      error={field.error}
                      required
                    />
                  </>
                )}
              </Field>
              <FieldLayout
                label={
                  <InputLabel help="Computed reference">Source Url</InputLabel>
                }
                field={
                  <InputLabel>
                    {getValue(formStore, "machine.flake") +
                      "#" +
                      getValue(formStore, "machine.devicePath")}
                  </InputLabel>
                }
              />
              <hr class="mb-6"></hr>

              <Field
                name="language"
                validate={[required("This field is required")]}
              >
                {(field, props) => (
                  <>
                    <SelectInput
                      selectProps={props}
                      label="Language"
                      value={String(field.value)}
                      error={field.error}
                      required
                      loading={langQuery.isLoading}
                      options={[
                        {
                          label: "en_US.UTF-8",
                          value: "en_US.UTF-8",
                        },
                        ...(langQuery.data?.map((lang) => ({
                          label: lang,
                          value: lang,
                        })) || []),
                      ]}
                    />
                  </>
                )}
              </Field>

              <Field
                name="keymap"
                validate={[required("This field is required")]}
              >
                {(field, props) => (
                  <>
                    <SelectInput
                      selectProps={props}
                      label="Keymap"
                      value={String(field.value)}
                      error={field.error}
                      required
                      loading={keymapQuery.isLoading}
                      options={[
                        {
                          label: "en",
                          value: "en",
                        },
                        ...(keymapQuery.data?.map((keymap) => ({
                          label: keymap,
                          value: keymap,
                        })) || []),
                      ]}
                    />
                  </>
                )}
              </Field>
            </div>
          </div>

          <hr></hr>
          <div class="mt-2 flex justify-end pt-2">
            <Button
              class="self-end"
              type="submit"
              disabled={formStore.submitting}
              startIcon={
                formStore.submitting ? (
                  <Icon icon="Load" />
                ) : (
                  <Icon icon="Flash" />
                )
              }
            >
              {formStore.submitting ? "Flashing..." : "Flash Installer"}
            </Button>
          </div>
        </Form>
      </div>
    </>
  );
};
