import { callApi } from "@/src/api";
import { Button } from "@/src/components/button";
import { FileInput } from "@/src/components/FileInput";
import Icon from "@/src/components/icon";
import { SelectInput } from "@/src/components/SelectInput";
import { TextInput } from "@/src/components/TextInput";
import { Typography } from "@/src/components/Typography";
import { Header } from "@/src/layout/header";
import {
  createForm,
  required,
  FieldValues,
  setValue,
  getValue,
} from "@modular-forms/solid";
import { createQuery } from "@tanstack/solid-query";
import { createEffect, createSignal, For, Show } from "solid-js";
import toast from "solid-toast";

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
      const result = await callApi("show_block_devices", {
        options: {},
      });
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

  const handleSubmit = async (values: FlashFormValues) => {
    console.log("Submit:", values);
    try {
      await callApi("flash_machine", {
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
      });
    } catch (error) {
      toast.error(`Error could not flash disk: ${error}`);
      console.error("Error submitting form:", error);
    }
  };

  return (
    <>
      <Header title="Flash installer" />
      <div class="p-4">
        <Typography tag="p" hierarchy="body" size="default" color="secondary">
          USB Utility image.
        </Typography>
        <Typography tag="p" hierarchy="body" size="default" color="secondary">
          This will make bootstrapping a new machine easier by providing secure
          remote connection to any machine when plugged in.
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
                topRightLabel={
                  <Button
                    size="s"
                    variant="light"
                    onClick={(e) => {
                      e.preventDefault();
                      deviceQuery.refetch();
                    }}
                    startIcon={<Icon icon="Update" />}
                  ></Button>
                }
                formStore={formStore}
                selectProps={props}
                label="Flash Disk"
                value={String(field.value)}
                error={field.error}
                required
                options={
                  <>
                    <option value="" disabled>
                      Select a disk where the installer will be flashed to
                    </option>

                    <For each={deviceQuery.data?.blockdevices}>
                      {(device) => (
                        <option value={device.path}>
                          {device.path} -- {device.size} bytes
                        </option>
                      )}
                    </For>
                  </>
                }
              />
            )}
          </Field>

          {/* WiFi Networks */}
          <div class="my-4 py-2">
            <h3 class="mb-2 text-lg font-semibold">WiFi Networks</h3>
            <span class="mb-2 text-sm">Add preconfigured networks</span>
            <For each={wifiNetworks()}>
              {(network, index) => (
                <div class="mb-2 grid grid-cols-7 gap-2">
                  <Field
                    name={`wifi.${index()}.ssid`}
                    validate={[required("SSID is required")]}
                  >
                    {(field, props) => (
                      <TextInput
                        formStore={formStore}
                        inputProps={props}
                        label="SSID"
                        value={field.value ?? ""}
                        error={field.error}
                        class="col-span-3"
                        required
                      />
                    )}
                  </Field>
                  <Field
                    name={`wifi.${index()}.password`}
                    validate={[required("Password is required")]}
                  >
                    {(field, props) => (
                      <div class="relative col-span-3 w-full">
                        <TextInput
                          formStore={formStore}
                          inputProps={props}
                          type={
                            passwordVisibility()[index()] ? "text" : "password"
                          }
                          label="Password"
                          value={field.value ?? ""}
                          error={field.error}
                          adornment={{
                            position: "end",
                            content: (
                              <Button
                                variant="light"
                                type="button"
                                class="flex justify-center opacity-70"
                                onClick={() =>
                                  togglePasswordVisibility(index())
                                }
                                startIcon={
                                  passwordVisibility()[index()] ? (
                                    <Icon icon="EyeClose" />
                                  ) : (
                                    <Icon icon="EyeOpen" />
                                  )
                                }
                              ></Button>
                            ),
                          }}
                          required
                        />
                      </div>
                    )}
                  </Field>
                  <div class="col-span-1 self-end">
                    <Button
                      type="button"
                      variant="light"
                      class="h-12"
                      onClick={() => removeWifiNetwork(index())}
                      startIcon={<Icon icon="Trash" />}
                    ></Button>
                  </div>
                </div>
              )}
            </For>
            <div class="">
              <Button
                type="button"
                size="s"
                variant="light"
                onClick={addWifiNetwork}
                startIcon={<Icon icon="Plus" />}
              >
                Add WiFi Network
              </Button>
            </div>
          </div>

          <div class="collapse collapse-arrow" tabindex="0">
            <input type="checkbox" />
            <div class="collapse-title link font-medium ">
              Advanced Settings
            </div>
            <div class="collapse-content">
              <Field
                name="machine.flake"
                validate={[required("This field is required")]}
              >
                {(field, props) => (
                  <>
                    <TextInput
                      formStore={formStore}
                      inputProps={props}
                      label="Source (flake URL)"
                      value={String(field.value)}
                      inlineLabel={
                        <span class="material-icons">file_download</span>
                      }
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
                      formStore={formStore}
                      inputProps={props}
                      label="Image Name (attribute name)"
                      value={String(field.value)}
                      inlineLabel={<span class="material-icons">devices</span>}
                      error={field.error}
                      required
                    />
                  </>
                )}
              </Field>
              <div class="my-2 py-2">
                <span class="text-sm text-neutral-600">Source URL: </span>
                <span class="text-sm text-neutral-600">
                  {getValue(formStore, "machine.flake") +
                    "#" +
                    getValue(formStore, "machine.devicePath")}
                </span>
              </div>
              <Field
                name="language"
                validate={[required("This field is required")]}
              >
                {(field, props) => (
                  <>
                    <SelectInput
                      formStore={formStore}
                      selectProps={props}
                      label="Language"
                      value={String(field.value)}
                      error={field.error}
                      required
                      options={
                        <>
                          <option value={"en_US.UTF-8"}>{"en_US.UTF-8"}</option>
                          <For each={langQuery.data}>
                            {(language) => (
                              <option value={language}>{language}</option>
                            )}
                          </For>
                        </>
                      }
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
                      formStore={formStore}
                      selectProps={props}
                      label="Keymap"
                      value={String(field.value)}
                      error={field.error}
                      required
                      options={
                        <>
                          <option value={"en"}>{"en"}</option>
                          <For each={keymapQuery.data}>
                            {(keymap) => (
                              <option value={keymap}>{keymap}</option>
                            )}
                          </For>
                        </>
                      }
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
