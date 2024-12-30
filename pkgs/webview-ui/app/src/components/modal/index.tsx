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
      const newTop = e.clientY - startOffset().y;
      const newLeft = e.clientX - startOffset().x;

      dialogRef.style.top = `${newTop}px`;
      dialogRef.style.left = `${newLeft}px`;
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
          class="absolute left-1/3 top-1/3 z-50 min-w-[320px] rounded-md border  border-def-4 focus-visible:outline-none"
          classList={{
            "!cursor-grabbing": dragging(),
            [cx("scale-105 transition-transform")]: dragging(),
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
            class="flex w-full justify-center rounded-t-md border-b-2 px-4 py-2 align-middle bg-def-3  border-def-5"
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
            <span class="mx-2"> {props.title}</span>
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
          <Dialog.Description class="flex flex-col bg-def-1" as="div">
            {props.children}
          </Dialog.Description>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog>
  );
};
