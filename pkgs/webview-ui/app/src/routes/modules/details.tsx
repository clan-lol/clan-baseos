import { callApi, SuccessData } from "@/src/api";
import { activeURI } from "@/src/App";
import { BackButton } from "@/src/components/BackButton";
import { createModulesQuery } from "@/src/queries";
import { useParams } from "@solidjs/router";
import { createEffect, For, Match, Show, Switch } from "solid-js";
import { SolidMarkdown } from "solid-markdown";
import toast from "solid-toast";
import { ModuleInfo } from "./list";
import { createQuery } from "@tanstack/solid-query";
import { JSONSchema4 } from "json-schema";
import { TextInput } from "@/src/components/TextInput";
import {
  createForm,
  getValue,
  setValue,
  SubmitHandler,
} from "@modular-forms/solid";

export const ModuleDetails = () => {
  const params = useParams();
  const modulesQuery = createModulesQuery(activeURI());

  return (
    <div class="p-1">
      <BackButton />
      <div class="p-2">
        <h3 class="text-2xl">{params.id}</h3>
        <Switch>
          <Match when={modulesQuery.data?.find((i) => i[0] === params.id)}>
            {(d) => <Details data={d()[1]} id={d()[0]} />}
          </Match>
        </Switch>
      </div>
    </div>
  );
};

function deepMerge(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  obj1: Record<string, any>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  obj2: Record<string, any>,
) {
  const result = { ...obj1 };

  for (const key in obj2) {
    if (Object.prototype.hasOwnProperty.call(obj2, key)) {
      if (obj2[key] instanceof Object && obj1[key] instanceof Object) {
        result[key] = deepMerge(obj1[key], obj2[key]);
      } else {
        result[key] = obj2[key];
      }
    }
  }

  return result;
}

interface DetailsProps {
  data: ModuleInfo;
  id: string;
}
const Details = (props: DetailsProps) => {
  return (
    <div class="flex w-full flex-col gap-2">
      <article class="prose">{props.data.description}</article>
      <span class="label-text">Categories</span>
      <div>
        <For each={props.data.categories}>
          {(c) => <div class="badge badge-primary m-1">{c}</div>}
        </For>
      </div>
      <span class="label-text">Roles</span>
      <div>
        <For each={props.data.roles}>
          {(r) => <div class="badge badge-secondary m-1">{r}</div>}
        </For>
      </div>
      <div class="p-2">
        <SolidMarkdown>{props.data.readme}</SolidMarkdown>
      </div>
      <div class="my-2 flex w-full gap-2">
        <button
          class="btn btn-primary"
          onClick={async () => {
            const uri = activeURI();
            if (!uri) return;
            const res = await callApi("get_inventory", { base_path: uri });
            if (res.status === "error") {
              toast.error("Failed to fetch inventory");
              return;
            }
            const inventory = res.data;
            const newInventory = deepMerge(inventory, {
              services: {
                [props.id]: {
                  default: {
                    enabled: false,
                  },
                },
              },
            });

            callApi("set_inventory", {
              flake_dir: uri,
              inventory: newInventory,
              message: `Add module: ${props.id} in 'default' instance`,
            });
          }}
        >
          <span class="material-icons ">add</span>
          Add to Clan
        </button>
      </div>
      <ModuleForm id={props.id} />
    </div>
  );
};

type ModuleSchemasType = Record<string, Record<string, JSONSchema4>>;

const Unsupported = (props: { schema: JSONSchema4; what: string }) => (
  <div>
    Cannot render {props.what}
    <pre>
      <code>{JSON.stringify(props.schema, null, 2)}</code>
    </pre>
  </div>
);

function removeTrailingS(str: string) {
  // Check if the last character is "s" or "S"
  if (str.endsWith("s") || str.endsWith("S")) {
    return str.slice(0, -1); // Remove the last character
  }
  return str; // Return unchanged if no trailing "s"
}
interface SchemaFormProps {
  title: string;
  schema: JSONSchema4;
  path: string[];
}

export const ModuleForm = (props: { id: string }) => {
  // TODO: Fetch the synced schema for all the modules at runtime
  // We use static schema file at build time for now. (Different versions might have different schema at runtime)
  const schemaQuery = createQuery(() => ({
    queryKey: [activeURI(), "modules_schema"],
    queryFn: async () => {
      const moduleSchema = await import(
        "../../../api/modules_schemas.json"
      ).then((m) => m.default as ModuleSchemasType);

      return moduleSchema;
    },
  }));

  createEffect(() => {
    console.log("Schema Query", schemaQuery.data?.[props.id]);
  });

  const [formStore, { Form, Field }] = createForm();
  const handleSubmit: SubmitHandler<NonNullable<unknown>> = async (
    values,
    event,
  ) => {
    console.log("Submitted form values", values);
  };
  const SchemaForm = (props: SchemaFormProps) => {
    return (
      <div>
        <Switch
          fallback={<Unsupported what={"schema"} schema={props.schema} />}
        >
          <Match when={props.schema.type === "object"}>
            <Switch
              fallback={<Unsupported what={"object"} schema={props.schema} />}
            >
              <Match
                when={
                  !props.schema.additionalProperties && props.schema.properties
                }
              >
                {(properties) => (
                  <For each={Object.entries(properties())}>
                    {([key, value]) => (
                      <SchemaForm
                        title={key}
                        schema={value}
                        path={[...props.path, key]}
                      />
                    )}
                  </For>
                )}
              </Match>
              <Match
                when={
                  typeof props.schema.additionalProperties == "object" &&
                  props.schema.additionalProperties
                }
              >
                {(additionalProperties) => (
                  <>
                    <div>{props.title}</div>
                    {/* @ts-expect-error: We don't know the field names ahead of time */}
                    <Field name={props.title}>
                      {(f, p) => (
                        <>
                          <Show when={f.value}>
                            <For
                              each={Object.entries(
                                f.value as Record<string, unknown>,
                              )}
                            >
                              {(v) => (
                                <div>
                                  <div>
                                    {removeTrailingS(props.title)}: {v[0]}
                                  </div>
                                  <div>
                                    <SchemaForm
                                      path={[...props.path, v[0]]}
                                      schema={additionalProperties()}
                                      title={v[0]}
                                    />{" "}
                                  </div>
                                </div>
                              )}
                            </For>
                          </Show>
                          <button
                            class="btn btn-ghost"
                            onClick={(e) => {
                              e.preventDefault();
                              const value = getValue(formStore, props.title);
                              setValue(formStore, props.title, {
                                // @ts-expect-error: TODO: check to be an object
                                ...value,
                                foo: {},
                              });
                            }}
                          >
                            Add
                          </button>
                        </>
                      )}
                    </Field>
                  </>
                )}
              </Match>
            </Switch>
          </Match>
          <Match when={props.schema.type === "array"}>
            TODO: Array field "{props.title}"
          </Match>
          <Match when={props.schema.type === "string"}>
            {/* @ts-expect-error: We dont know the field names ahead of time */}
            <Field name={props.path.join(".")}>
              {(field, fieldProps) => (
                <TextInput
                  formStore={formStore}
                  inputProps={fieldProps}
                  label={props.title}
                  // @ts-expect-error: It is a string, otherwise the json schema would be invalid
                  value={field.value ?? ""}
                  error={field.error}
                />
              )}
            </Field>
          </Match>
        </Switch>
      </div>
    );
  };

  return (
    <div id="ModuleForm">
      <Switch fallback={"No Schema found"}>
        <Match when={schemaQuery.isLoading}>Loading...</Match>
        <Match when={schemaQuery.data?.[props.id]}>
          {(rolesSchemas) => (
            <>
              Configure this module
              <For each={Object.entries(rolesSchemas())}>
                {([role, schema]) => (
                  <div class="my-2">
                    <h4 class="text-xl">{role}</h4>
                    <Form onSubmit={handleSubmit}>
                      <SchemaForm title={role} schema={schema} path={[]} />
                      <br />
                      <button class="btn btn-primary">Save</button>
                    </Form>
                  </div>
                )}
              </For>
            </>
          )}
        </Match>
      </Switch>
    </div>
  );
};
