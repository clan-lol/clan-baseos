import { useNavigate } from "@solidjs/router";

export const BackButton = () => {
  const navigate = useNavigate();
  return (
    <button class="btn btn-square btn-ghost" onClick={() => navigate(-1)}>
      <span class="material-icons ">arrow_back_ios</span>
    </button>
  );
};
