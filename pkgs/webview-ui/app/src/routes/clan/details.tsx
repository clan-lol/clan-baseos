import { callApi, SuccessQuery } from "@/src/api";
import { BackButton } from "@/src/components/BackButton";
import { useParams } from "@solidjs/router";
import { createQuery } from "@tanstack/solid-query";
import { createSignal, For, Match, Switch } from "solid-js";
import { Show } from "solid-js";
import {
  createForm,
  FieldValues,
  getValue,
  getValues,
  setValue,
} from "@modular-forms/solid";
import { TextInput } from "@/src/components/TextInput";
import toast from "solid-toast";

type AdminData = SuccessQuery<"get_admin_service">["data"];

interface ClanDetailsProps {
  admin: AdminData;
  base_url: string;
}
interface AdminSettings extends FieldValues {
  allowedKeys: { name: string; value: string }[];
}

const ClanDetails = (props: ClanDetailsProps) => {
  const items = () =>
    Object.entries<string>(
      (props.admin?.config?.allowedKeys as Record<string, string>) || {},
    );
  const [formStore, { Form, Field }] = createForm<AdminSettings>({
    initialValues: {
      allowedKeys: items().map(([name, value]) => ({ name, value })),
    },
  });

  const [keys, setKeys] = createSignal<1[]>(
    new Array(items().length || 1).fill(1),
  );

  const handleSubmit = async (values: AdminSettings) => {
    console.log("submitting", values, getValues(formStore));

    const r = await callApi("set_admin_service", {
      base_url: props.base_url,
      allowed_keys: values.allowedKeys.reduce(
        (acc, curr) => ({ ...acc, [curr.name]: curr.value }),
        {},
      ),
    });
    if (r.status === "success") {
      toast.success("Successfully updated admin settings");
    }
    if (r.status === "error") {
      toast.error(`Failed to update admin settings: ${r.errors[0].message}`);
    }
  };

  return (
    <div>
      <span class="text-xl text-primary">Clan Admin Settings</span>
      <Form onSubmit={handleSubmit}>
        <div class="grid grid-cols-12 gap-2">
          <span class="col-span-12 text-lg text-neutral">
            Each of the following keys can be used to authenticate on any
            machine
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
                          <div class="input input-bordered relative flex items-center gap-2">
                            <input
                              value=""
                              // Disable drag n drop
                              onDrop={(e) => e.preventDefault()}
                              class="absolute -ml-4 size-full cursor-pointer opacity-0"
                              type="file"
                              onInput={async (e) => {
                                console.log(e.target.files);
                                if (!e.target.files) return;

                                const content = await e.target.files[0].text();
                                console.log(content);
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
        </div>
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
          <button class="btn" type="submit">
            Submit
          </button>
        </div>
      </Form>
    </div>
  );
};

export const Details = () => {
  const params = useParams();
  const clan_dir = window.atob(params.id);
  const query = createQuery(() => ({
    queryKey: [clan_dir, "get_admin_service"],
    queryFn: async () => {
      const result = await callApi("get_admin_service", {
        base_url: clan_dir,
      });
      if (result.status === "error") throw new Error("Failed to fetch data");
      return result.data || null;
    },
  }));

  return (
    <div class="p-2">
      <BackButton />
      <Show
        when={!query.isLoading}
        fallback={<span class="loading loading-lg"></span>}
      >
        <Switch>
          <Match when={query.data}>
            {(d) => <ClanDetails admin={query.data} base_url={clan_dir} />}
          </Match>
        </Switch>
      </Show>
    </div>
  );
};
