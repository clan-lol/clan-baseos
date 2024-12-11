import { callApi, ClanServiceInstance, SuccessQuery } from "@/src/api";
import { useParams } from "@solidjs/router";
import { createQuery, useQueryClient } from "@tanstack/solid-query";
import { createSignal, For, Match, Switch } from "solid-js";
import {
  createForm,
  FieldValues,
  getValue,
  getValues,
  required,
  setValue,
  SubmitHandler,
} from "@modular-forms/solid";
import { TextInput } from "@/src/components/TextInput";
import toast from "solid-toast";
import { set_single_service } from "@/src/api/inventory";
import { Button } from "@/src/components/button";
import Icon from "@/src/components/icon";
import { Header } from "@/src/layout/header";

interface AdminModuleFormProps {
  admin: AdminData;
  base_url: string;
}
interface AdminSettings extends FieldValues {
  allowedKeys: { name: string; value: string }[];
}

interface EditClanFormProps {
  initial: GeneralData;
  directory: string;
}

const EditClanForm = (props: EditClanFormProps) => {
  const [formStore, { Form, Field }] = createForm<GeneralData>({
    initialValues: props.initial,
  });
  const queryClient = useQueryClient();

  const handleSubmit: SubmitHandler<GeneralData> = async (values, event) => {
    await toast.promise(
      (async () => {
        await callApi("update_clan_meta", {
          options: {
            directory: props.directory,
            meta: values,
          },
        });
      })(),
      {
        loading: "Updating clan...",
        success: "Clan Successfully updated",
        error: "Failed to update clan",
      },
    );
    queryClient.invalidateQueries({
      queryKey: [props.directory, "meta"],
    });
  };
  const curr_name = () => props.initial.name;

  return (
    <Form onSubmit={handleSubmit} shouldActive>
      <Field name="icon">
        {(field) => (
          <>
            <div class="flex flex-col items-center">
              <div class="text-3xl text-primary-800">{curr_name()}</div>
              <div class="text-secondary-800">Wide settings</div>
              <Icon
                class="mt-4"
                icon="ClanIcon"
                viewBox="0 0 72 89"
                width={96}
                height={96}
              />
            </div>
          </>
        )}
      </Field>
      <div class="card-body">
        <span class="text-xl text-primary-800">General</span>
        <Field
          name="name"
          validate={[required("Please enter a unique name for the clan.")]}
        >
          {(field, props) => (
            <label class="form-control w-full">
              <div class="label">
                <span class="label-text block after:ml-0.5 after:text-primary-800 after:content-['*']">
                  Name
                </span>
              </div>

              <input
                {...props}
                disabled={formStore.submitting}
                required
                placeholder="Clan Name"
                class="input input-bordered"
                classList={{ "input-error": !!field.error }}
                value={field.value}
              />
              <div class="label">
                {field.error && (
                  <span class="label-text-alt">{field.error}</span>
                )}
              </div>
            </label>
          )}
        </Field>
        <Field name="description">
          {(field, props) => (
            <label class="form-control w-full">
              <div class="label">
                <span class="label-text">Description</span>
              </div>

              <input
                {...props}
                disabled={formStore.submitting}
                required
                type="text"
                placeholder="Some words about your clan"
                class="input input-bordered"
                classList={{ "input-error": !!field.error }}
                value={field.value || ""}
              />
              <div class="label">
                {field.error && (
                  <span class="label-text-alt">{field.error}</span>
                )}
              </div>
            </label>
          )}
        </Field>
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
  );
};

const AdminModuleForm = (props: AdminModuleFormProps) => {
  const items = () =>
    Object.entries<string>(
      (props.admin?.config?.allowedKeys as Record<string, string>) || {},
    );
  const [formStore, { Form, Field }] = createForm<AdminSettings>({
    initialValues: {
      allowedKeys: items().map(([name, value]) => ({ name, value })),
    },
  });
  const queryClient = useQueryClient();

  const [keys, setKeys] = createSignal<1[]>(
    new Array(items().length || 1).fill(1),
  );

  const handleSubmit = async (values: AdminSettings) => {
    console.log("submitting", values, getValues(formStore));

    const r = await set_single_service(
      queryClient,
      props.base_url,
      "",
      "admin",
      {
        meta: {
          name: "admin",
        },
        roles: {
          default: {
            tags: ["all"],
          },
        },
        config: {
          allowedKeys: values.allowedKeys.reduce(
            (acc, curr) => ({ ...acc, [curr.name]: curr.value }),
            {},
          ),
        },
      },
    );
    if (r.status === "success") {
      toast.success("Successfully updated admin settings");
    }
    if (r.status === "error") {
      toast.error(`Failed to update admin settings: ${r.errors[0].message}`);
    }
    queryClient.invalidateQueries({
      queryKey: [props.base_url, "get_admin_service"],
    });
  };

  return (
    <Form onSubmit={handleSubmit}>
      <div class="card-body">
        <span class="text-xl text-primary-800">Administration</span>
        <div class="grid grid-cols-12 gap-2">
          <span class="col-span-12 text-lg text-neutral-800">
            Each of the following keys can be used to authenticate on machines
          </span>
          <For each={keys()}>
            {(name, idx) => (
              <>
                <Field name={`allowedKeys.${idx()}.name`}>
                  {(field, props) => (
                    <TextInput
                      formStore={formStore}
                      inputProps={props}
                      label={"Name"}
                      adornment={{
                        position: "start",
                        content: (
                          <span class="material-icons text-gray-400">key</span>
                        ),
                      }}
                      value={field.value ?? ""}
                      error={field.error}
                      class="col-span-4"
                      required
                    />
                  )}
                </Field>
                <Field name={`allowedKeys.${idx()}.value`}>
                  {(field, props) => (
                    <>
                      <TextInput
                        formStore={formStore}
                        inputProps={props}
                        label={"Value"}
                        value={field.value ?? ""}
                        error={field.error}
                        class="col-span-6"
                        required
                      />
                      <span class="tooltip mt-auto" data-tip="Select file">
                        <label
                          class={"form-control w-full"}
                          aria-disabled={formStore.submitting}
                        >
                          <div class="btn btn-secondary relative flex items-center justify-center">
                            <input
                              value=""
                              // Disable drag n drop
                              onDrop={(e) => e.preventDefault()}
                              class="absolute -ml-4 size-full cursor-pointer opacity-0"
                              type="file"
                              onInput={async (e) => {
                                if (!e.target.files) return;

                                const content = await e.target.files[0].text();
                                setValue(
                                  formStore,
                                  `allowedKeys.${idx()}.value`,
                                  content,
                                );
                                if (
                                  !getValue(
                                    formStore,
                                    `allowedKeys.${idx()}.name`,
                                  )
                                ) {
                                  setValue(
                                    formStore,
                                    `allowedKeys.${idx()}.name`,
                                    e.target.files[0].name,
                                  );
                                }
                              }}
                            />
                            <span class="material-icons">file_open</span>
                          </div>
                        </label>
                      </span>
                    </>
                  )}
                </Field>
                <Button
                  variant="light"
                  class="col-span-1 self-end"
                  startIcon={<Icon icon="Trash" />}
                  onClick={(e) => {
                    e.preventDefault();
                    setKeys((c) => c.filter((_, i) => i !== idx()));
                    setValue(formStore, `allowedKeys.${idx()}.name`, "");
                    setValue(formStore, `allowedKeys.${idx()}.value`, "");
                  }}
                ></Button>
              </>
            )}
          </For>
          <div class="my-2 flex w-full gap-2">
            <Button
              variant="light"
              onClick={(e) => {
                e.preventDefault();
                setKeys((c) => [...c, 1]);
              }}
              startIcon={<Icon icon="Plus" />}
            ></Button>
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
  );
};

type GeneralData = SuccessQuery<"show_clan_meta">["data"];
type AdminData = ClanServiceInstance<"admin">;

export const ClanDetails = () => {
  const params = useParams();
  const clan_dir = window.atob(params.id);
  // Fetch general meta data
  const clanQuery = createQuery(() => ({
    queryKey: [clan_dir, "inventory", "meta"],
    queryFn: async () => {
      const result = await callApi("show_clan_meta", { uri: clan_dir });
      if (result.status === "error") throw new Error("Failed to fetch data");
      return result.data;
    },
  }));

  return (
    <>
      <Header title={clan_dir} showBack />
      <div class="flex flex-col justify-center">
        <Switch fallback={<>General data not available</>}>
          <Match when={clanQuery.data}>
            {(d) => <EditClanForm initial={d()} directory={clan_dir} />}
          </Match>
        </Switch>
      </div>
    </>
  );
};
