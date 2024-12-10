import { RndThumbnail } from "@/src/components/noiseThumbnail";
import cx from "classnames";
interface AvatarProps {
  name?: string;
  class?: string;
}
export const MachineAvatar = (props: AvatarProps) => {
  return (
    <figure>
      <div class="avatar placeholder">
        <div
          class={cx(
            "rounded-lg border p-2 bg-def-1 border-def-3 size-36",
            props.class,
          )}
        >
          <RndThumbnail name={props.name || ""} />
        </div>
      </div>
    </figure>
  );
};
