import { Button } from ".";
import FlashIcon from "@/icons/flash.svg";

export const Test = () => {
  <div class="p-8">
    <Button>Label</Button>
    <Button
      startIcon={<FlashIcon width={16} height={16} viewBox="0 0 48 48" />}
    >
      Label
    </Button>
    <Button
      variant="light"
      endIcon={<FlashIcon width={16} height={16} viewBox="0 0 48 48" />}
    >
      Label
    </Button>
    <Button size="s">Label</Button>
    <Button
      variant="light"
      size="s"
      endIcon={<FlashIcon width={13} height={13} viewBox="0 0 48 48" />}
    >
      Label
    </Button>
  </div>;
};
