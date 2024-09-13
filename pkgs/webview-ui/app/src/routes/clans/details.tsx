import {
  callApi,
  ClanService,
  ClanServiceInstance,
  SuccessQuery,
} from "@/src/api";
import { BackButton } from "@/src/components/BackButton";
import { useParams } from "@solidjs/router";
import {
  createQuery,
  QueryClient,
  useQueryClient,
} from "@tanstack/solid-query";
import { createSignal, For, Match, Switch } from "solid-js";
import { Show } from "solid-js";
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
import { get_single_service, set_single_service } from "@/src/api/inventory";

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
            <figure class="p-1">
              <div class="flex flex-col items-center">
                <div class="text-3xl text-primary">{curr_name()}</div>
                <div class="text-secondary">Wide settings</div>
              </div>
            </figure>
            <figure>
              <Show
                when={field.value}
                fallback={
                  <span class="material-icons aspect-square size-60 rounded-lg text-[18rem]">
                    group
                  </span>
                }
              >
                {(icon) => (
                  <img
                    class="aspect-square size-60 rounded-lg"
                    src={icon()}
                    alt="Clan Logo"
                  />
                )}
              </Show>
            </figure>
          </>
        )}
      </Field>
      <div class="card-body">
        <span class="text-xl text-primary">General</span>
        <Field
          name="name"
          validate={[required("Please enter a unique name for the clan.")]}
        >
          {(field, props) => (
            <label class="form-control w-full">
              <div class="label">
                <span class="label-text block after:ml-0.5 after:text-primary after:content-['*']">
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
            <button
              class="btn btn-primary"
              type="submit"
              disabled={formStore.submitting || !formStore.dirty}
            >
              Save
            </button>
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
        <span class="text-xl text-primary">Administration</span>
        <div class="grid grid-cols-12 gap-2">
          <span class="col-span-12 text-lg text-neutral">
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
                <button
                  class="btn btn-ghost col-span-1 self-end"
                  onClick={(e) => {
                    e.preventDefault();
                    setKeys((c) => c.filter((_, i) => i !== idx()));
                    setValue(formStore, `allowedKeys.${idx()}.name`, "");
                    setValue(formStore, `allowedKeys.${idx()}.value`, "");
                  }}
                >
                  <span class="material-icons">delete</span>
                </button>
              </>
            )}
          </For>
          <div class="my-2 flex w-full gap-2">
            <button
              class="btn btn-square btn-ghost"
              onClick={(e) => {
                e.preventDefault();
                setKeys((c) => [...c, 1]);
              }}
            >
              <span class="material-icons">add</span>
            </button>
          </div>
        </div>
        {
          <div class="card-actions justify-end">
            <button
              class="btn btn-primary"
              type="submit"
              disabled={formStore.submitting || !formStore.dirty}
            >
              Save
            </button>
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
  const queryClient = useQueryClient();
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
  // Fetch admin settings
  const adminQuery = createQuery(() => ({
    queryKey: [clan_dir, "inventory", "services", "admin"],
    queryFn: async () => {
      const result = await get_single_service(queryClient, clan_dir, "admin");
      if (!result) throw new Error("Failed to fetch data");
      return result;
    },
  }));

  return (
    <div class="card card-normal">
      <BackButton />
      <Show
        when={!adminQuery.isLoading}
        fallback={
          <div>
            <span class="loading loading-lg"></span>
          </div>
        }
      >
        <Switch fallback={<>General data not available</>}>
          <Match when={clanQuery.data}>
            {(d) => <EditClanForm initial={d()} directory={clan_dir} />}
          </Match>
        </Switch>
      </Show>
      <div class="divider"></div>
      <Show
        when={!adminQuery.isLoading}
        fallback={
          <div>
            <span class="loading loading-lg"></span>
          </div>
        }
      >
        <Switch fallback={<>Admin data not available</>}>
          <Match when={adminQuery.data}>
            {(d) => <AdminModuleForm admin={d()} base_url={clan_dir} />}
          </Match>
        </Switch>
      </Show>
    </div>
  );
};
