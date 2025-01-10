import Dialog from "corvu/dialog";
import { createSignal, JSX } from "solid-js";
import { Button } from "../button";
import Icon from "../icon";
import cx from "classnames";

interface ModalProps {
  open: boolean | undefined;
  handleClose: () => void;
  title: string;
  children: JSX.Element;
  class?: string;
}
export const Modal = (props: ModalProps) => {
  const [dragging, setDragging] = createSignal(false);
  const [startOffset, setStartOffset] = createSignal({ x: 0, y: 0 });

  let dialogRef: HTMLDivElement;

  const handleMouseDown = (e: MouseEvent) => {
    setDragging(true);
    const rect = dialogRef.getBoundingClientRect();
    setStartOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (dragging()) {
      let newTop = e.clientY - startOffset().y;
      let newLeft = e.clientX - startOffset().x;

      if (newTop < 0) {
        newTop = 0;
      }
      if (newLeft < 0) {
        newLeft = 0;
      }
      dialogRef.style.top = `${newTop}px`;
      dialogRef.style.left = `${newLeft}px`;

      // dialogRef.style.maxHeight = `calc(100vh - ${newTop}px - 2rem)`;
      // dialogRef.style.maxHeight = `calc(100vh - ${newTop}px - 2rem)`;
    }
  };

  const handleMouseUp = () => setDragging(false);

  return (
    <Dialog open={props.open} trapFocus={true}>
      <Dialog.Portal>
        <Dialog.Overlay
          class="fixed inset-0 z-50 bg-black/50"
          onMouseMove={handleMouseMove}
        />

        <Dialog.Content
          class={cx(
            "overflow-hidden absolute left-1/3 top-1/3 z-50 min-w-[560px] rounded-md border border-def-4 focus-visible:outline-none",
            props.class,
          )}
          classList={{
            "!cursor-grabbing": dragging(),
            [cx("scale-[101%] transition-transform")]: dragging(),
          }}
          ref={(el) => {
            dialogRef = el;
          }}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseDown={(e: MouseEvent) => {
            e.stopPropagation(); // Prevent backdrop drag conflict
          }}
          onClick={(e: MouseEvent) => e.stopPropagation()} // Prevent backdrop click closing
        >
          <Dialog.Label
            as="div"
            class="flex w-full justify-center border-b-2 px-4 py-2 align-middle bg-def-3  border-def-5"
            onMouseDown={handleMouseDown}
          >
            <div
              class="flex w-full cursor-move flex-col gap-px py-1 "
              classList={{
                "!cursor-grabbing": dragging(),
              }}
            >
              <hr class="h-px w-full border-none bg-secondary-300" />
              <hr class="h-px w-full border-none bg-secondary-300" />
              <hr class="h-px w-full border-none bg-secondary-300" />
              <hr class="h-px w-full border-none bg-secondary-300" />
              <hr class="h-px w-full border-none bg-secondary-300" />
              <hr class="h-px w-full border-none bg-secondary-300" />
            </div>
            <span class="mx-2 select-none whitespace-nowrap">
              {props.title}
            </span>
            <div
              class="flex w-full cursor-move flex-col gap-px py-1 "
              classList={{
                "!cursor-grabbing": dragging(),
              }}
            >
              <hr class="h-px w-full border-none bg-secondary-300" />
              <hr class="h-px w-full border-none bg-secondary-300" />
              <hr class="h-px w-full border-none bg-secondary-300" />
              <hr class="h-px w-full border-none bg-secondary-300" />
              <hr class="h-px w-full border-none bg-secondary-300" />
              <hr class="h-px w-full border-none bg-secondary-300" />
            </div>

            <div class="absolute right-1 top-2 pl-1 bg-def-3">
              <Button
                onMouseDown={(e) => e.stopPropagation()}
                tabIndex={-1}
                class="size-4"
                variant="ghost"
                onClick={() => props.handleClose()}
                size="s"
                startIcon={<Icon icon={"Close"} />}
              />
            </div>
          </Dialog.Label>
          <Dialog.Description
            class="flex max-h-[90vh] flex-col overflow-y-hidden bg-def-1"
            as="div"
          >
            {props.children}
          </Dialog.Description>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog>
  );
};
