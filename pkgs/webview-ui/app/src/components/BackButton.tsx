import { useNavigate } from "@solidjs/router";
import { Button } from "./button";
import Icon from "./icon";

export const BackButton = () => {
  const navigate = useNavigate();
  return (
    <Button
      variant="ghost"
      size="s"
      class="mr-2"
      onClick={() => navigate(-1)}
      startIcon={<Icon icon="CaretLeft" />}
    ></Button>
  );
};
