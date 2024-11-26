import { useNavigate } from "@solidjs/router";
import { Button } from "./button";
import Icon from "./icon";

export const BackButton = () => {
  const navigate = useNavigate();
  return (
    <Button
      variant="light"
      class="w-fit"
      onClick={() => navigate(-1)}
      startIcon={<Icon icon="ArrowLeft" />}
    ></Button>
  );
};
