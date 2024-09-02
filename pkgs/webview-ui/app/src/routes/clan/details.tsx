import { callApi, SuccessData } from "@/src/api";
import { BackButton } from "@/src/components/BackButton";
import { useParams } from "@solidjs/router";
import { createQuery } from "@tanstack/solid-query";
import { createEffect, createSignal, For, Match, Switch } from "solid-js";
import { Show } from "solid-js";
import { DiskView } from "../disk/view";
import { Accessor } from "solid-js";
import {
  createForm,
  FieldArray,
  FieldValues,
  getValue,
  getValues,
  insert,
  setValue,
} from "@modular-forms/solid";
import { TextInput } from "@/src/components/TextInput";

type AdminData = SuccessData<"get_admin_service">["data"];

interface ClanDetailsProps {
  admin: AdminData;
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

  const [keys, setKeys] = createSignal<1[]>(new Array(items().length).fill(1));

  const handleSubmit = async (values: AdminSettings) => {
    console.log("submitting", values, getValues(formStore));
  };
  return (
    <div>
      <span class="text-xl text-primary">Clan Settings</span>
      <br></br>
      <span class="text-lg text-neutral">
        Each of the following keys can be used to authenticate on any machine
      </span>
      <Form onSubmit={handleSubmit}>
        <div class="grid grid-cols-12 gap-2">
          <For each={keys()}>
            {(name, idx) => (
              <>
                <Field name={`allowedKeys.${idx()}.name`}>
                  {(field, props) => (
                    <TextInput
                      formStore={formStore}
                      inputProps={props}
                      label={`allowedKeys.${idx()}.name-` + items().length}
                      value={field.value ?? ""}
                      error={field.error}
                      class="col-span-4"
                      required
                    />
                  )}
                </Field>
                <Field name={`allowedKeys.${idx()}.value`}>
                  {(field, props) => (
                    <TextInput
                      formStore={formStore}
                      inputProps={props}
                      label="Value"
                      value={field.value ?? ""}
                      error={field.error}
                      class="col-span-7"
                      required
                    />
                  )}
                </Field>
                <button class="btn btn-ghost col-span-1 self-end">
                  <span class="material-icons">delete</span>
                </button>
              </>
            )}
          </For>
        </div>
        <div class="flex w-full my-2 gap-2">
          <button
            class="btn btn-ghost btn-square"
            onClick={(e) => {
              e.preventDefault();
              setKeys((c) => [...c, 1]);
              console.log(keys());
            }}
          >
            <span class="material-icons">add</span>
          </button>
          <button class="btn">Submit</button>
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
            {(d) => <ClanDetails admin={query.data} />}
          </Match>
        </Switch>
      </Show>
    </div>
  );
};
