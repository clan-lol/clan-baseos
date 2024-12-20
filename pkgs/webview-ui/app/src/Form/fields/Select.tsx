import {
  createUniqueId,
  createSignal,
  Show,
  type JSX,
  For,
  createMemo,
} from "solid-js";
import { Portal } from "solid-js/web";
import { useFloating } from "../base";
import { autoUpdate, flip, hide, offset, shift, size } from "@floating-ui/dom";
import { Button } from "@/src/components/button";
import {
  InputBase,
  InputError,
  InputLabel,
  InputLabelProps,
} from "@/src/components/inputBase";
import { FieldLayout } from "./layout";
import Icon from "@/src/components/icon";

export interface Option {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SelectInputpProps {
  value: string[] | string;
  selectProps: JSX.InputHTMLAttributes<HTMLSelectElement>;
  options: Option[];
  label: JSX.Element;
  labelProps?: InputLabelProps;
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
  loading?: boolean;
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
      offset({ mainAxis: 2 }),
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
      <FieldLayout
        error={props.error && <InputError error={props.error} />}
        label={
          <InputLabel
            description={""}
            required={props.required}
            {...props.labelProps}
          >
            {props.label}
          </InputLabel>
        }
        field={
          <>
            <InputBase
              error={!!props.error}
              disabled={props.disabled}
              required={props.required}
              class="!justify-start"
              divRef={setReference}
              inputElem={
                <button
                  // TODO: Keyboard acessibililty
                  // Currently the popover only opens with onClick
                  // Options are not selectable with keyboard
                  tabIndex={-1}
                  onClick={() => {
                    const popover = document.getElementById(_id);
                    if (popover) {
                      popover.togglePopover(); // Show or hide the popover
                    }
                  }}
                  type="button"
                  class="flex w-full items-center gap-2"
                  formnovalidate
                  // TODO: Use native popover once Webkit supports it within <form>
                  // popovertarget={_id}
                  // popovertargetaction="toggle"
                >
                  <Show
                    when={
                      props.adornment && props.adornment.position === "start"
                    }
                  >
                    {props.adornment?.content}
                  </Show>
                  {props.inlineLabel}
                  <div class="flex cursor-default flex-row gap-2">
                    <Show
                      when={
                        getValues() &&
                        getValues.length !== 1 &&
                        getValues()[0] !== ""
                      }
                      fallback={props.placeholder}
                    >
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
                    </Show>
                  </div>
                  <Show
                    when={props.adornment && props.adornment.position === "end"}
                  >
                    {props.adornment?.content}
                  </Show>
                  <Icon icon="CaretDown" class="ml-auto mr-2"></Icon>
                </button>
              }
            />
          </>
        }
      />

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
          class="z-[1] shadow"
        >
          <ul class="menu flex max-h-96 flex-col gap-1 overflow-x-hidden overflow-y-scroll">
            <Show when={!props.loading} fallback={"Loading ...."}>
              <For each={props.options}>
                {(opt) => (
                  <>
                    <li>
                      <Button
                        variant="ghost"
                        class="!justify-start"
                        onClick={() => handleClickOption(opt)}
                        disabled={opt.disabled}
                        classList={{
                          active:
                            !opt.disabled && getValues().includes(opt.value),
                        }}
                      >
                        {opt.label}
                      </Button>
                    </li>
                  </>
                )}
              </For>
            </Show>
          </ul>
        </div>
      </Portal>
    </>
  );
}
