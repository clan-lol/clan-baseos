import {
  createForm,
  Field,
  FieldArray,
  FieldElement,
  FieldValues,
  FormStore,
  getValue,
  minLength,
  pattern,
  ResponseData,
  setValue,
  getValues,
  insert,
  SubmitHandler,
  swap,
  reset,
  remove,
  move,
  setError,
  setValues,
} from "@modular-forms/solid";
import { JSONSchema7, JSONSchema7Type, validate } from "json-schema";
import { TextInput } from "../fields/TextInput";
import {
  children,
  Component,
  createEffect,
  For,
  JSX,
  Match,
  Show,
  Switch,
} from "solid-js";
import cx from "classnames";
import { Label } from "../base/label";
import { SelectInput } from "../fields/Select";
import { Button } from "@/src/components/button";
import Icon from "@/src/components/icon";

function generateDefaults(schema: JSONSchema7): unknown {
  switch (schema.type) {
    case "string":
      return ""; // Default value for string

    case "number":
    case "integer":
      return 0; // Default value for number/integer

    case "boolean":
      return false; // Default value for boolean

    case "array":
      return []; // Default empty array if no items schema or items is true/false

    case "object": {
      const obj: Record<string, unknown> = {};
      if (schema.properties) {
        Object.entries(schema.properties).forEach(([key, propSchema]) => {
          if (typeof propSchema === "boolean") {
            obj[key] = false;
          } else {
            // if (schema.required  schema.required.includes(key))
            obj[key] = generateDefaults(propSchema);
          }
        });
      }
      return obj;
    }

    default:
      return null; // Default for unknown types or nulls
  }
}

interface FormProps {
  schema: JSONSchema7;
  initialValues?: NonNullable<unknown>;
  handleSubmit?: SubmitHandler<NonNullable<unknown>>;
  initialPath?: string[];
  components?: {
    before?: JSX.Element;
    after?: JSX.Element;
  };
  readonly?: boolean;
  formProps?: JSX.InputHTMLAttributes<HTMLFormElement>;
  errorContext?: string;
  resetOnSubmit?: boolean;
}
export const DynForm = (props: FormProps) => {
  const [formStore, { Field, Form: ModuleForm }] = createForm({
    initialValues: props.initialValues,
  });

  const handleSubmit: SubmitHandler<NonNullable<unknown>> = async (
    values,
    event,
  ) => {
    console.log("Submitting form values", values, props.errorContext);
    props.handleSubmit?.(values, event);
    // setValue(formStore, "root", null);
    if (props.resetOnSubmit) {
      console.log("Resetting form", values, props.initialValues);
      reset(formStore);
    }
  };

  createEffect(() => {
    console.log("FormStore", formStore);
  });

  return (
    <>
      <ModuleForm {...props.formProps} onSubmit={handleSubmit}>
        {props.components?.before}
        <SchemaFields
          schema={props.schema}
          Field={Field}
          formStore={formStore}
          path={props.initialPath || []}
          readonly={!!props.readonly}
          parent={props.schema}
        />
        {props.components?.after}
      </ModuleForm>
    </>
  );
};

interface UnsupportedProps {
  schema: JSONSchema7;
  error?: string;
}

const Unsupported = (props: UnsupportedProps) => (
  <div>
    {props.error && <div class="font-bold text-error-700">{props.error}</div>}
    <span>
      Invalid or unsupported schema entry of type:{" "}
      <b>{JSON.stringify(props.schema.type)}</b>
    </span>
    <pre>
      <code>{JSON.stringify(props.schema, null, 2)}</code>
    </pre>
  </div>
);

interface SchemaFieldsProps<T extends FieldValues, R extends ResponseData> {
  formStore: FormStore<T, R>;
  Field: typeof Field<T, R, never>;
  schema: JSONSchema7;
  path: string[];
  readonly: boolean;
  parent: JSONSchema7;
}
export function SchemaFields<T extends FieldValues, R extends ResponseData>(
  props: SchemaFieldsProps<T, R>,
) {
  return (
    <Switch fallback={<Unsupported schema={props.schema} />}>
      {/* Simple types */}
      <Match when={props.schema.type === "boolean"}>bool</Match>

      <Match when={props.schema.type === "integer"}>
        <StringField {...props} schema={props.schema} />
      </Match>
      <Match when={props.schema.type === "number"}>
        <StringField {...props} schema={props.schema} />
      </Match>
      <Match when={props.schema.type === "string"}>
        <StringField {...props} schema={props.schema} />
      </Match>
      {/* Composed types */}
      <Match when={props.schema.type === "array"}>
        <ArrayFields {...props} schema={props.schema} />
      </Match>
      <Match when={props.schema.type === "object"}>
        <ObjectFields {...props} schema={props.schema} />
      </Match>
      {/* Empty / Null */}
      <Match when={props.schema.type === "null"}>
        Dont know how to rendner InputType null
        <Unsupported schema={props.schema} />
      </Match>
    </Switch>
  );
}

export function StringField<T extends FieldValues, R extends ResponseData>(
  props: SchemaFieldsProps<T, R>,
) {
  if (
    props.schema.type !== "string" &&
    props.schema.type !== "number" &&
    props.schema.type !== "integer"
  ) {
    return (
      <span class="text-error-700">
        Error cannot render the following as String input.
        <Unsupported schema={props.schema} />
      </span>
    );
  }
  const { Field } = props;

  const validate = props.schema.pattern
    ? pattern(
        new RegExp(props.schema.pattern),
        `String should follow pattern ${props.schema.pattern}`,
      )
    : undefined;

  const commonProps = {
    label: props.schema.title || props.path.join("."),
    required:
      props.parent.required &&
      props.parent.required.some(
        (r) => r === props.path[props.path.length - 1],
      ),
  };
  const readonly = props.readonly;
  return (
    <Switch fallback={<Unsupported schema={props.schema} />}>
      <Match
        when={props.schema.type === "number" || props.schema.type === "integer"}
      >
        {(s) => (
          <Field
            // @ts-expect-error: We dont know dynamic names while type checking
            name={props.path.join(".")}
            validate={validate}
          >
            {(field, fieldProps) => (
              <>
                <TextInput
                  inputProps={{
                    ...fieldProps,
                    inputmode: "numeric",
                    pattern: "[0-9.]*",
                    readonly,
                  }}
                  {...commonProps}
                  value={(field.value as unknown as string) || ""}
                  error={field.error}
                  // required
                  // altLabel="Leave empty to accept the default"
                  // helperText="Configure how dude connects"
                  // error="Something is wrong now"
                />
              </>
            )}
          </Field>
        )}
      </Match>
      <Match when={props.schema.enum}>
        {(_enumSchemas) => (
          <Field
            // @ts-expect-error: We dont know dynamic names while type checking
            name={props.path.join(".")}
          >
            {(field, fieldProps) => (
              <OnlyStringItems itemspec={props.schema}>
                {(options) => (
                  <SelectInput
                    error={field.error}
                    altLabel={props.schema.title}
                    label={props.path.join(".")}
                    helperText={props.schema.description}
                    value={field.value || []}
                    options={options.map((o) => ({
                      value: o,
                      label: o,
                    }))}
                    selectProps={fieldProps}
                    required={!!props.schema.minItems}
                  />
                )}
              </OnlyStringItems>
            )}
          </Field>
        )}
      </Match>
      <Match when={props.schema.writeOnly && props.schema}>
        {(s) => (
          <Field
            // @ts-expect-error: We dont know dynamic names while type checking
            name={props.path.join(".")}
            validate={validate}
          >
            {(field, fieldProps) => (
              <TextInput
                inputProps={{ ...fieldProps, readonly }}
                value={field.value as unknown as string}
                type="password"
                error={field.error}
                {...commonProps}
                // required
                // altLabel="Leave empty to accept the default"
                // helperText="Configure how dude connects"
                // error="Something is wrong now"
              />
            )}
          </Field>
        )}
      </Match>
      {/* TODO: when is it a normal string input? */}
      <Match when={props.schema}>
        {(s) => (
          <Field
            // @ts-expect-error: We dont know dynamic names while type checking
            name={props.path.join(".")}
            validate={validate}
          >
            {(field, fieldProps) => (
              <TextInput
                inputProps={{ ...fieldProps, readonly }}
                value={field.value as unknown as string}
                error={field.error}
                {...commonProps}
                // placeholder="foobar"
                // inlineLabel={
                //   <div class="label">
                //     <span class="label-text"></span>
                //   </div>
                // }
                // required
                // altLabel="Leave empty to accept the default"
                // helperText="Configure how dude connects"
                // error="Something is wrong now"
              />
            )}
          </Field>
        )}
      </Match>
    </Switch>
  );
}

interface OptionSchemaProps {
  itemSpec: JSONSchema7Type;
}
export function OptionSchema(props: OptionSchemaProps) {
  return (
    <Switch
      fallback={<option class="text-error-700">Item spec unhandled</option>}
    >
      <Match when={typeof props.itemSpec === "string" && props.itemSpec}>
        {(o) => <option>{o()}</option>}
      </Match>
    </Switch>
  );
}

interface ValueDisplayProps<T extends FieldValues, R extends ResponseData>
  extends SchemaFieldsProps<T, R> {
  children: JSX.Element;
  listFieldName: string;
  idx: number;
  of: number;
}
export function ListValueDisplay<T extends FieldValues, R extends ResponseData>(
  props: ValueDisplayProps<T, R>,
) {
  const removeItem = (e: Event) => {
    e.preventDefault();
    remove(
      props.formStore,
      // @ts-expect-error: listFieldName is not known ahead of time
      props.listFieldName,
      { at: props.idx },
    );
  };
  const moveItemBy = (dir: number) => (e: Event) => {
    e.preventDefault();
    move(
      props.formStore,
      // @ts-expect-error: listFieldName is not known ahead of time
      props.listFieldName,
      { from: props.idx, to: props.idx + dir },
    );
  };
  const topMost = () => props.idx === props.of - 1;
  const bottomMost = () => props.idx === 0;

  return (
    <div class="w-full border-l-4 border-gray-300">
      <div class="flex w-full items-end gap-2 px-4">
        {props.children}
        <div class="ml-4 min-w-fit pb-4">
          <Button
            variant="light"
            onClick={moveItemBy(1)}
            disabled={topMost()}
            startIcon={<Icon icon="ArrowBottom" />}
            class="h-12"
          ></Button>
          <Button
            variant="light"
            onClick={moveItemBy(-1)}
            disabled={bottomMost()}
            class="h-12"
            startIcon={<Icon icon="ArrowTop" />}
          ></Button>
          <Button
            class="h-12"
            startIcon={<Icon icon="Trash" />}
            onClick={removeItem}
          ></Button>
        </div>
      </div>
    </div>
  );
}

const findDuplicates = (arr: unknown[]) => {
  const seen = new Set();
  const duplicates: number[] = [];

  arr.forEach((obj, idx) => {
    const serializedObj = JSON.stringify(obj);

    if (seen.has(serializedObj)) {
      duplicates.push(idx);
    } else {
      seen.add(serializedObj);
    }
  });

  return duplicates;
};

interface OnlyStringItems {
  children: (items: string[]) => JSX.Element;
  itemspec: JSONSchema7;
}
const OnlyStringItems = (props: OnlyStringItems) => {
  return (
    <Show
      when={
        Array.isArray(props.itemspec.enum) &&
        typeof props.itemspec.type === "string" &&
        props.itemspec
      }
      fallback={
        <Unsupported
          schema={props.itemspec}
          error="Unsupported array item type"
        />
      }
    >
      {props.children(props.itemspec.enum as string[])}
    </Show>
  );
};

export function ArrayFields<T extends FieldValues, R extends ResponseData>(
  props: SchemaFieldsProps<T, R>,
) {
  if (props.schema.type !== "array") {
    return (
      <span class="text-error-700">
        Error cannot render the following as array.
        <Unsupported schema={props.schema} />
      </span>
    );
  }
  const { Field } = props;

  const listFieldName = props.path.join(".");

  return (
    <>
      <Switch fallback={<Unsupported schema={props.schema} />}>
        <Match
          when={
            !Array.isArray(props.schema.items) &&
            typeof props.schema.items === "object" &&
            props.schema.items
          }
        >
          {(itemsSchema) => (
            <>
              <Switch fallback={<Unsupported schema={props.schema} />}>
                <Match when={itemsSchema().type === "array"}>
                  <Unsupported
                    schema={props.schema}
                    error="Array of Array is not supported yet."
                  />
                </Match>
                <Match
                  when={itemsSchema().type === "string" && itemsSchema().enum}
                >
                  <Field
                    // @ts-expect-error: listFieldName is not known ahead of time
                    name={listFieldName}
                    // @ts-expect-error: type is known due to schema
                    type="string[]"
                    validateOn="touched"
                    revalidateOn="touched"
                    validate={() => {
                      let error = "";
                      const values: unknown[] = getValues(
                        props.formStore,
                        // @ts-expect-error: listFieldName is not known ahead of time
                        listFieldName,
                        // @ts-expect-error: assumption based on the behavior of selectInput
                      )?.strings?.selection;
                      console.log("vali", { values });
                      if (props.schema.uniqueItems) {
                        const duplicates = findDuplicates(values);
                        if (duplicates.length) {
                          error = `Duplicate entries are not allowed. Please make sure each entry is unique.`;
                        }
                      }
                      if (
                        props.schema.maxItems &&
                        values.length > props.schema.maxItems
                      ) {
                        error = `You can only select up to ${props.schema.maxItems} items`;
                      }
                      if (
                        props.schema.minItems &&
                        values.length < props.schema.minItems
                      ) {
                        error = `Please select at least ${props.schema.minItems} items.`;
                      }
                      return error;
                    }}
                  >
                    {(field, fieldProps) => (
                      <OnlyStringItems itemspec={itemsSchema()}>
                        {(options) => (
                          <SelectInput
                            multiple
                            error={field.error}
                            altLabel={props.schema.title}
                            label={listFieldName}
                            helperText={props.schema.description}
                            value={field.value || ""}
                            options={options.map((o) => ({
                              value: o,
                              label: o,
                            }))}
                            selectProps={fieldProps}
                            required={!!props.schema.minItems}
                          />
                        )}
                      </OnlyStringItems>
                    )}
                  </Field>
                </Match>

                <Match
                  when={
                    itemsSchema().type === "string" ||
                    itemsSchema().type === "object"
                  }
                >
                  {/* !Important: Register the parent field to gain access to array items*/}
                  <FieldArray
                    // @ts-expect-error: listFieldName is not known ahead of time
                    name={listFieldName}
                    of={props.formStore}
                    validateOn="touched"
                    revalidateOn="touched"
                    validate={() => {
                      let error = "";
                      // @ts-expect-error: listFieldName is not known ahead of time
                      const values: unknown[] = getValues(
                        props.formStore,
                        // @ts-expect-error: listFieldName is not known ahead of time
                        listFieldName,
                      );
                      if (props.schema.uniqueItems) {
                        const duplicates = findDuplicates(values);
                        if (duplicates.length) {
                          error = `Duplicate entries are not allowed. Please make sure each entry is unique.`;
                        }
                      }
                      if (
                        props.schema.maxItems &&
                        values.length > props.schema.maxItems
                      ) {
                        error = `You can only add up to ${props.schema.maxItems} items`;
                      }
                      if (
                        props.schema.minItems &&
                        values.length < props.schema.minItems
                      ) {
                        error = `Please add at least ${props.schema.minItems} items.`;
                      }

                      return error;
                    }}
                  >
                    {(fieldArray) => (
                      <>
                        {/* Render existing items */}
                        <For
                          each={fieldArray.items}
                          fallback={
                            // Empty list
                            <span class="text-neutral-500">No items</span>
                          }
                        >
                          {(item, idx) => (
                            <ListValueDisplay
                              {...props}
                              listFieldName={listFieldName}
                              idx={idx()}
                              of={fieldArray.items.length}
                            >
                              <Field
                                // @ts-expect-error: field names are not know ahead of time
                                name={`${listFieldName}.${idx()}`}
                              >
                                {(f, fp) => (
                                  <>
                                    <DynForm
                                      formProps={{
                                        class: cx("w-full"),
                                      }}
                                      resetOnSubmit={true}
                                      schema={itemsSchema()}
                                      initialValues={
                                        itemsSchema().type === "object"
                                          ? f.value
                                          : { "": f.value }
                                      }
                                      readonly={true}
                                    ></DynForm>
                                  </>
                                )}
                              </Field>
                            </ListValueDisplay>
                          )}
                        </For>
                        <span class="label-text-alt font-bold text-error-700">
                          {fieldArray.error}
                        </span>

                        {/* Add new item */}
                        <DynForm
                          formProps={{
                            class: cx("px-2 w-full"),
                          }}
                          schema={{ ...itemsSchema(), title: "Add entry" }}
                          initialPath={["root"]}
                          // Reset the input field for list items
                          resetOnSubmit={true}
                          initialValues={{
                            root: generateDefaults(itemsSchema()),
                          }}
                          // Button for adding new items
                          components={{
                            before: (
                              <Button
                                variant="light"
                                endIcon={<Icon icon={"Plus"} />}
                              >
                                Add
                              </Button>
                            ),
                          }}
                          // Add the new item to the FieldArray
                          handleSubmit={(values, event) => {
                            // @ts-expect-error: listFieldName is not known ahead of time
                            const prev: unknown[] = getValues(
                              props.formStore,

                              // @ts-expect-error: listFieldName is not known ahead of time
                              listFieldName,
                            );
                            if (itemsSchema().type === "object") {
                              const newIdx = prev.length;
                              setValue(
                                props.formStore,

                                // @ts-expect-error: listFieldName is not known ahead of time
                                `${listFieldName}.${newIdx}`,

                                // @ts-expect-error: listFieldName is not known ahead of time
                                values.root,
                              );
                            }

                            // @ts-expect-error: listFieldName is not known ahead of time
                            insert(props.formStore, listFieldName, {
                              // @ts-expect-error: listFieldName is not known ahead of time
                              value: values.root,
                            });
                          }}
                        />
                      </>
                    )}
                  </FieldArray>
                </Match>
              </Switch>
            </>
          )}
        </Match>
      </Switch>
    </>
  );
}

interface ObjectFieldPropertyLabelProps {
  schema: JSONSchema7;
  fallback: JSX.Element;
}
export function ObjectFieldPropertyLabel(props: ObjectFieldPropertyLabelProps) {
  return (
    <Switch fallback={props.fallback}>
      {/* @ts-expect-error: $exportedModuleInfo should exist since we export it */}
      <Match when={props.schema?.$exportedModuleInfo?.path}>
        {(path) => path()[path().length - 1]}
      </Match>
    </Switch>
  );
}

export function ObjectFields<T extends FieldValues, R extends ResponseData>(
  props: SchemaFieldsProps<T, R>,
) {
  if (props.schema.type !== "object") {
    return (
      <span class="text-error-700">
        Error cannot render the following as Object
        <Unsupported schema={props.schema} />
      </span>
    );
  }

  const fieldName = props.path.join(".");
  const { Field } = props;

  return (
    <Switch
      fallback={
        <Unsupported
          schema={props.schema}
          error="Dont know how to render objectFields"
        />
      }
    >
      <Match
        when={!props.schema.additionalProperties && props.schema.properties}
      >
        {(properties) => (
          <For each={Object.entries(properties())}>
            {([propName, propSchema]) => (
              <div
                // eslint-disable-next-line tailwindcss/no-custom-classname
                class={cx(
                  "w-full grid grid-cols-1 gap-4 justify-items-start",
                  `p-${props.path.length * 2}`,
                )}
              >
                <Label
                  label={propName}
                  required={props.schema.required?.some((r) => r === propName)}
                />

                {typeof propSchema === "object" && (
                  <SchemaFields
                    {...props}
                    schema={propSchema}
                    path={[...props.path, propName]}
                  />
                )}
                {typeof propSchema === "boolean" && (
                  <span class="text-error-700">
                    Schema: Object of Boolean not supported
                  </span>
                )}
              </div>
            )}
          </For>
        )}
      </Match>
      {/* Objects where people can define their own keys
        - Trivial Key-value pairs. Where the value is a string a number or a list of strings (trivial select).
        - Non-trivial Key-value pairs. Where the value is an object or a list
      */}
      <Match
        when={
          typeof props.schema.additionalProperties === "object" &&
          props.schema.additionalProperties
        }
      >
        {(additionalPropertiesSchema) => (
          <Switch
            fallback={
              <Unsupported
                schema={additionalPropertiesSchema()}
                error="type of additionalProperties not supported yet"
              />
            }
          >
            {/* Non-trivival cases */}
            <Match
              when={
                additionalPropertiesSchema().type === "object" &&
                additionalPropertiesSchema()
              }
            >
              {(itemSchema) => (
                <Field
                  // Important!: Register the object field to gain access to the dynamic object properties
                  // @ts-expect-error: fieldName is not known ahead of time
                  name={fieldName}
                >
                  {(objectField, fp) => (
                    <>
                      <For
                        fallback={
                          <>
                            <label class="label-text">
                              No{" "}
                              <ObjectFieldPropertyLabel
                                schema={itemSchema()}
                                fallback={"No entries"}
                              />{" "}
                              yet.
                            </label>
                          </>
                        }
                        each={Object.entries(objectField.value || {})}
                      >
                        {([key, relatedValue]) => (
                          <Field
                            // @ts-expect-error: fieldName is not known ahead of time
                            name={`${fieldName}.${key}`}
                          >
                            {(f, fp) => (
                              <div class="w-full border-l-4 border-gray-300 pl-4">
                                <DynForm
                                  formProps={{
                                    class: cx("w-full"),
                                  }}
                                  schema={itemSchema()}
                                  initialValues={f.value}
                                  components={{
                                    before: (
                                      <div class="flex w-full">
                                        <span class="text-xl font-semibold">
                                          {key}
                                        </span>
                                        <Button
                                          variant="light"
                                          class="ml-auto"
                                          size="s"
                                          type="button"
                                          onClick={(_e) => {
                                            const copy = {
                                              // @ts-expect-error: fieldName is not known ahead of time
                                              ...objectField.value,
                                            };
                                            // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
                                            delete copy[key];
                                            setValue(
                                              props.formStore,
                                              // @ts-expect-error: fieldName is not known ahead of time
                                              `${fieldName}`,
                                              copy,
                                            );
                                          }}
                                        >
                                          <Icon icon="Trash" />
                                        </Button>
                                      </div>
                                    ),
                                  }}
                                />
                              </div>
                            )}
                          </Field>
                        )}
                      </For>
                      {/* Replace this with a normal input ?*/}
                      <DynForm
                        formProps={{
                          class: cx("w-full"),
                        }}
                        resetOnSubmit={true}
                        initialValues={{ "": "" }}
                        schema={{
                          type: "string",
                          title: `Entry title or key`,
                        }}
                        handleSubmit={(values, event) => {
                          setValue(
                            props.formStore,
                            // @ts-expect-error: fieldName is not known ahead of time
                            `${fieldName}`,
                            // @ts-expect-error: fieldName is not known ahead of time
                            { ...objectField.value, [values[""]]: {} },
                          );
                        }}
                      />
                    </>
                  )}
                </Field>
              )}
            </Match>
            <Match
              when={
                additionalPropertiesSchema().type === "array" &&
                additionalPropertiesSchema()
              }
            >
              {(itemSchema) => (
                <Unsupported
                  schema={itemSchema()}
                  error="dynamic arrays are not implemented yet"
                />
              )}
            </Match>
            {/* TODO: Trivial cases */}
          </Switch>
        )}
      </Match>
    </Switch>
  );
}
