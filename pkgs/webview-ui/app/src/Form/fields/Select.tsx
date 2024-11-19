import {
  createUniqueId,
  createSignal,
  Show,
  type JSX,
  For,
  createMemo,
} from "solid-js";
import { Portal } from "solid-js/web";
import cx from "classnames";
import { Label } from "../base/label";
import { useFloating } from "../base";
import { autoUpdate, flip, hide, shift, size } from "@floating-ui/dom";

export interface Option {
  value: string;
  label: string;
}

interface SelectInputpProps {
  value: string[] | string;
  selectProps: JSX.InputHTMLAttributes<HTMLSelectElement>;
  options: Option[];
  label: JSX.Element;
  altLabel?: JSX.Element;
  helperText?: JSX.Element;
  error?: string;
  required?: boolean;
  type?: string;
  inlineLabel?: JSX.Element;
  class?: string;
  adornment?: {
    position: "start" | "end";
    content: JSX.Element;
  };
  disabled?: boolean;
  placeholder?: string;
  multiple?: boolean;
}

export function SelectInput(props: SelectInputpProps) {
  const _id = createUniqueId();

  const [reference, setReference] = createSignal<HTMLElement>();
  const [floating, setFloating] = createSignal<HTMLElement>();

  // `position` is a reactive object.
  const position = useFloating(reference, floating, {
    placement: "bottom-start",

    // pass options. Ensure the cleanup function is returned.
    whileElementsMounted: (reference, floating, update) =>
      autoUpdate(reference, floating, update, {
        animationFrame: true,
      }),
    middleware: [
      size({
        apply({ rects, elements }) {
          Object.assign(elements.floating.style, {
            minWidth: `${rects.reference.width}px`,
          });
        },
      }),
      shift(),
      flip(),
      hide({
        strategy: "referenceHidden",
      }),
    ],
  });

  // Create values list
  const getValues = createMemo(() => {
    return Array.isArray(props.value)
      ? (props.value as string[])
      : typeof props.value === "string"
        ? [props.value]
        : [];
  });

  // const getSingleValue = createMemo(() => {
  //   const values = getValues();
  //   return values.length > 0 ? values[0] : "";
  // });

  const handleClickOption = (opt: Option) => {
    if (!props.multiple) {
      // @ts-expect-error: fieldName is not known ahead of time
      props.selectProps.onInput({
        currentTarget: {
          value: opt.value,
        },
      });
      return;
    }
    let currValues = getValues();

    if (currValues.includes(opt.value)) {
      currValues = currValues.filter((o) => o !== opt.value);
    } else {
      currValues.push(opt.value);
    }
    // @ts-expect-error: fieldName is not known ahead of time
    props.selectProps.onInput({
      currentTarget: {
        options: currValues.map((value) => ({
          value,
          selected: true,
          disabled: false,
        })),
      },
    });
  };

  return (
    <>
      <label
        class={cx("form-control w-full", props.class)}
        aria-disabled={props.disabled}
      >
        <div class="label">
          <Label label={props.label} required={props.required} />
          <span class="label-text-alt block">{props.altLabel}</span>
        </div>
        <button
          type="button"
          class="select select-bordered flex items-center gap-2"
          ref={setReference}
          popovertarget={_id}
        >
          <Show when={props.adornment && props.adornment.position === "start"}>
            {props.adornment?.content}
          </Show>
          {props.inlineLabel}
          <div class="flex cursor-default flex-row gap-2">
            <For each={getValues()} fallback={"Select"}>
              {(item) => (
                <div class="rounded-xl bg-slate-800 px-4 py-1 text-sm text-white">
                  {item}
                  <Show when={props.multiple}>
                    <button
                      class="btn-ghost btn-xs"
                      type="button"
                      onClick={(_e) => {
                        // @ts-expect-error: fieldName is not known ahead of time
                        props.selectProps.onInput({
                          currentTarget: {
                            options: getValues()
                              .filter((o) => o !== item)
                              .map((value) => ({
                                value,
                                selected: true,
                                disabled: false,
                              })),
                          },
                        });
                      }}
                    >
                      X
                    </button>
                  </Show>
                </div>
              )}
            </For>
          </div>
          <select
            class="hidden"
            multiple
            {...props.selectProps}
            required={props.required}
          >
            <For each={props.options}>
              {({ label, value }) => (
                <option value={value} selected={getValues().includes(value)}>
                  {label}
                </option>
              )}
            </For>
          </select>
          <Show when={props.adornment && props.adornment.position === "end"}>
            {props.adornment?.content}
          </Show>
        </button>
        <Portal mount={document.body}>
          <div
            id={_id}
            popover
            ref={setFloating}
            style={{
              margin: 0,
              position: position.strategy,
              top: `${position.y ?? 0}px`,
              left: `${position.x ?? 0}px`,
            }}
            class="dropdown-content z-[1] rounded-b-box bg-base-100 shadow"
          >
            <ul class="menu flex max-h-96 flex-col gap-1 overflow-x-hidden overflow-y-scroll">
              <For each={props.options}>
                {(opt) => (
                  <>
                    <li>
                      <button
                        onClick={() => handleClickOption(opt)}
                        classList={{
                          active: getValues().includes(opt.value),
                        }}
                      >
                        {opt.label}
                      </button>
                    </li>
                  </>
                )}
              </For>
            </ul>
          </div>
        </Portal>
        <div class="label">
          {props.helperText && (
            <span class="label-text text-neutral">{props.helperText}</span>
          )}
          {props.error && (
            <span class="label-text-alt font-bold text-error-700">
              {props.error}
            </span>
          )}
        </div>
      </label>
    </>
  );
}
